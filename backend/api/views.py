from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from datetime import timedelta
from .models import Building, Room, Student, User, Invoice, SystemSettings, Complaint
from .pagination import StandardResultsSetPagination
from .serializers import (
    BuildingSerializer, RoomSerializer, StudentSerializer,
    UserSerializer, InvoiceSerializer, SystemSettingsSerializer,
    ComplaintSerializer,
)
from .permissions import IsAdminUser, IsDelegate, IsAccountant, IsAuthenticatedCustom, IsAdminOrAccountant, IsAdminOrDelegate, IsAdminOrAccountantOrCashier
from .exceptions import OverdueInvoiceError, NotFoundError, ValidationError, MeterCommandError
from .services   import MeterCommandService


class PingView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "ok", "message": "Server is awake"})


class BuildingViewSet(viewsets.ModelViewSet):
    pagination_class = None
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'floor_plan']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['get'])
    def floor_plan(self, request, pk=None):
        building = self.get_object()
        rooms = building.rooms.all().prefetch_related('students', 'invoices', 'manual_meter_actions')
        
        floor_plan_data = []
        for room in rooms:
            student = room.students.filter(status='active').first()
            latest_invoice = room.invoices.order_by('-created_at').first()
            latest_action = room.manual_meter_actions.order_by('-performed_at').first()
            
            # Determine status
            room_status = 'gray' # Default if no data
            if latest_action and latest_action.action_type == 'disconnect':
                room_status = 'black'
            elif latest_invoice:
                if latest_invoice.status == 'paid':
                    room_status = 'green'
                else:
                    room_status = 'red'
            
            # Get search_code (reusing logic)
            search_code = f"{room.room_number}0{building.code}" if building.code in ['1', '2'] else str(room.room_number)

            floor_plan_data.append({
                'id': room.id,
                'room_number': room.room_number,
                'search_code': search_code,
                'student_name': student.name if student else 'شاغرة',
                'status': room_status,
                'consumption': latest_invoice.consumption if latest_invoice else 0.0,
                'amount_due': latest_invoice.final_amount if latest_invoice else 0.0
            })
            
        return Response({
            'building': building.name,
            'rooms': floor_plan_data
        })


class RoomViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultsSetPagination
    queryset = Room.objects.select_related('building').all()
    serializer_class = RoomSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = super().get_queryset()
        building_id = self.request.query_params.get('building')
        search_param = self.request.query_params.get('search')
        if building_id:
            queryset = queryset.filter(building_id=building_id)
        if search_param:
            queryset = queryset.filter(
                Q(room_number__icontains=search_param) |
                Q(qr_code__icontains=search_param)
            )
        return queryset


class StudentViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultsSetPagination
    queryset = Student.objects.select_related('room').all()
    serializer_class = StudentSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = super().get_queryset()
        room_id = self.request.query_params.get('room')
        if room_id:
            queryset = queryset.filter(room_id=room_id)
        return queryset


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = super().get_queryset()
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        return queryset


class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.select_related('student', 'student__room').all().order_by('-created_at')
    serializer_class = ComplaintSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticatedCustom]
        else:
            permission_classes = [IsAdminOrAccountant]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get('status')
        student_id = self.request.query_params.get('student')
        if status_param:
            queryset = queryset.filter(status=status_param)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        return queryset


class PublicRoomInvoiceView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, qr_code, *args, **kwargs):
        try:
            room = Room.objects.get(qr_code=qr_code)
        except Room.DoesNotExist:
            return Response({'success': False, 'message': 'الغرفة غير موجودة.'}, status=404)

        # Get the latest invoice for this room
        invoice = Invoice.objects.filter(room=room).order_by('-created_at').first()
        
        if not invoice:
            return Response({'success': False, 'message': 'لا توجد فواتير مسجلة لهذه الغرفة.'}, status=404)

        serializer = InvoiceSerializer(invoice)
        return Response({
            'success': True,
            'room': RoomSerializer(room).data,
            'invoice': serializer.data
        })


class InvoiceViewSet(viewsets.ModelViewSet):
    pagination_class = StandardResultsSetPagination
    queryset = Invoice.objects.select_related('room', 'created_by', 'approved_by').all()
    serializer_class = InvoiceSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAdminOrDelegate]
        elif self.action in ['approve', 'mark_paid']:
            permission_classes = [IsAdminOrAccountant]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticatedCustom]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get('status')
        room_id = self.request.query_params.get('room')
        search_param = self.request.query_params.get('search')
        if status_param:
            if status_param == 'overdue':
                queryset = queryset.filter(is_overdue=True)
            else:
                queryset = queryset.filter(status=status_param)
        if room_id:
            queryset = queryset.filter(room_id=room_id)
        if search_param:
            queryset = queryset.filter(
                Q(room__room_number__icontains=search_param) |
                Q(room__qr_code__icontains=search_param)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        from decimal import Decimal
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reading_old = Decimal(str(serializer.validated_data.get('reading_old') or 0))
        reading_new = Decimal(str(serializer.validated_data.get('reading_new') or 0))
        room = serializer.validated_data.get('room')
        
        consumption = reading_new - reading_old

        confirm_anomaly = request.data.get('confirm_anomaly', False)
        if isinstance(confirm_anomaly, str):
            confirm_anomaly = confirm_anomaly.lower() in ('true', '1', 't', 'y', 'yes')

        is_override_logged = False
        audit_metadata = None

        past_invoices = Invoice.objects.filter(room=room, status='approved').order_by('-created_at')[:3]
        if len(past_invoices) >= 2:
            avg_consumption = sum((Decimal(str(inv.consumption)) for inv in past_invoices if inv.consumption is not None), Decimal('0')) / Decimal(len(past_invoices))
            
            if avg_consumption > Decimal('0'):
                settings_obj = SystemSettings.get_settings()
                threshold_percentage = Decimal(str(settings_obj.anomaly_threshold_percentage))
                
                threshold_multiplier = Decimal('1.0') + (threshold_percentage / Decimal('100.0'))
                
                if consumption > (avg_consumption * threshold_multiplier):
                    percentage_increase = ((consumption - avg_consumption) / avg_consumption) * Decimal('100.0')
                    if not confirm_anomaly:
                        return Response({
                            'success': False,
                            'is_anomaly': True,
                            'new_consumption': float(consumption),
                            'average_consumption': float(avg_consumption),
                            'increase_percentage': float(percentage_increase),
                            'message': 'تم اكتشاف استهلاك شاذ. يرجى مراجعة القراءة وتأكيدها إن كانت صحيحة.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        is_override_logged = True
                        audit_metadata = {
                            'new_consumption': float(consumption),
                            'average_consumption': float(avg_consumption),
                            'increase_percentage': float(percentage_increase)
                        }

        self.perform_create(serializer)
        
        if is_override_logged:
            from .services.audit_service import AuditLogger
            AuditLogger.log(
                actor=request.user,
                action_type='anomaly_override',
                target_model='Invoice',
                target_id=str(serializer.instance.id),
                description='تجاوز المندوب تحذير الاستهلاك الشاذ',
                metadata=audit_metadata
            )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        reading_old = serializer.validated_data.get('reading_old') or 0
        reading_new = serializer.validated_data.get('reading_new') or 0
        unit_price = serializer.validated_data.get('unit_price') or 0
        previous_debt = serializer.validated_data.get('previous_debt') or 0

        consumption = reading_new - reading_old
        total_amount = consumption * unit_price
        final_amount = total_amount + previous_debt

        serializer.save(
            created_by=self.request.user,
            consumption=consumption,
            total_amount=total_amount,
            final_amount=final_amount,
        )

    def _check_overdue(self, invoice) -> None:
        """
        يتحقق مما إذا كانت الفاتورة قد تجاوزت مهلة السداد.
        • إن كانت متأخرة لأول مرة: يُحدِّث is_overdue وoverdue_fine ثم يرمي OverdueInvoiceError.
        • إن كانت متأخرة مسبقاً: يرمي OverdueInvoiceError مباشرةً بالغرامة المحفوظة.
        • يُعفى منها الفواتير المدفوعة.
        """
        from .models import SystemSettings
        if invoice.status == 'paid':
            return

        settings_obj = SystemSettings.get_settings()
        deadline = invoice.created_at + timedelta(hours=settings_obj.payment_deadline_hours)

        if timezone.now() > deadline:
            if not invoice.is_overdue:
                # أول تجاوز للمهلة — نسجّل الغرامة ونحفظ
                fine = float(settings_obj.service_fee)
                invoice.is_overdue   = True
                invoice.overdue_fine = fine
                invoice.save(update_fields=['is_overdue', 'overdue_fine'])
                raise OverdueInvoiceError(overdue_fine=fine)
            else:
                # الغرامة مسجّلة مسبقاً
                raise OverdueInvoiceError(overdue_fine=float(invoice.overdue_fine))

    def retrieve(self, request, *args, **kwargs):
        """
        تحديث صامت لحالة التأخير عند استعراض تفاصيل الفاتورة.
        لا يرمي استثناء — فقط يُحدِّث الحقول إن لزم الأمر.
        """
        invoice = self.get_object()

        if invoice.status != 'paid' and not invoice.is_overdue:
            settings_obj = SystemSettings.get_settings()
            deadline = invoice.created_at + timedelta(hours=settings_obj.payment_deadline_hours)
            if timezone.now() > deadline:
                invoice.is_overdue   = True
                invoice.overdue_fine = settings_obj.service_fee
                invoice.save(update_fields=['is_overdue', 'overdue_fine'])

        serializer = self.get_serializer(invoice)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        invoice = self.get_object()

        if invoice.status != 'pending':
            return Response(
                {"error": "هذي الفاتورة معتمدة مسبقاً أو مدفوعة."},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoice.status = 'approved'
        invoice.approved_by = request.user
        invoice.save()

        serializer = self.get_serializer(invoice)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()

        if invoice.status != 'approved':
            return Response(
                {"error": "لازم تعتمد الفاتورة أولاً قبل تحديدها كمدفوعة."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # يتحقق من التأخير ويرمي OverdueInvoiceError إن وُجد
        self._check_overdue(invoice)

        invoice.status = 'paid'
        invoice.paid_at = timezone.now()
        invoice.save()

        serializer = self.get_serializer(invoice)
        return Response(serializer.data)


    """
    عرض وتحديث الإعدادات المالية العامة للنظام — Singleton.

    GET   — متاح لأي مستخدم مصادق عليه.
    PUT   — تحديث كامل (مشرف فقط).
    PATCH — تحديث جزئي (مشرف فقط).
    """

    def get_permissions(self):
        """
        مكافئ get_permissions في ViewSet — يختار الصلاحية بحسب نوع الطلب.
        """
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAdminUser()]
        return [IsAuthenticatedCustom()]

    def get(self, request):
        """عرض الإعدادات الحالية"""
        settings_obj = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings_obj)
        return Response({'success': True, 'data': serializer.data})

    def put(self, request):
        """تحديث كامل — جميع الحقول مطلوبة"""
        return self._update(request, partial=False)

    def patch(self, request):
        """تحديث جزئي — يكفي إرسال الحقول المراد تغييرها"""
        return self._update(request, partial=True)

    def _update(self, request, partial: bool):
        """منطق مشترك لـ PUT و PATCH — يتحقق من البيانات ثم يحفظ"""
        settings_obj = SystemSettings.get_settings()
        old_data = SystemSettingsSerializer(settings_obj).data
        serializer = SystemSettingsSerializer(
            settings_obj, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        new_data = serializer.data
        
        changed_fields = {k: {'old': old_data.get(k), 'new': new_data.get(k)} 
                          for k in new_data if old_data.get(k) != new_data.get(k)}
        if changed_fields:
            from .services.audit_service import AuditLogger
            AuditLogger.log(
                actor=request.user,
                action_type='system_settings_updated',
                target_model='SystemSettings',
                target_id='1',
                description='تم تحديث الإعدادات العامة للنظام',
                metadata={'changed_fields': changed_fields}
            )
            
        return Response({'success': True, 'data': serializer.data})


class VerifyTransactionView(APIView):
    """
    التحقق من كود المحفظة الإلكترونية.
    """
    permission_classes = [IsAuthenticatedCustom]

    def post(self, request):
        from .models import Transaction
        from .exceptions import InvalidTransactionError

        transaction_id = request.data.get('transaction_id')
        wallet_provider = request.data.get('wallet_provider')
        room_id = request.data.get('room_id')
        amount = request.data.get('amount')

        if not all([transaction_id, wallet_provider, room_id, amount]):
            raise ValidationError("البيانات المطلوبة غير مكتملة (transaction_id, wallet_provider, room_id, amount)")

        # 1. تحقق من عدم تكرار transaction_id
        if Transaction.objects.filter(transaction_id=transaction_id).exists():
            raise InvalidTransactionError()

        # 2. إنشاء المعاملة بحالة pending
        transaction = Transaction.objects.create(
            transaction_id=transaction_id,
            room_id=room_id,
            wallet_provider=wallet_provider,
            amount=amount,
            verification_status='pending'
        )

        # 3. استدعاء بوابة الدفع الآلية للتحقق الفوري
        from .services.payment_gateway_service import PaymentGatewayService
        
        try:
            verification_result = PaymentGatewayService.verify_transaction(
                transaction_id=transaction_id,
                wallet_provider=wallet_provider,
                amount=amount,
                user=request.user
            )
        except Exception:
            verification_result = 'unavailable'

        if verification_result == 'verified':
            # التحقق الآلي ناجح -> تحديث الحالة وتسوية الدفع فوراً
            transaction.verification_status = 'verified'
            transaction.save()
            
            # نسخ البيانات الحالية في قاموس جديد لضمان قابليتها للتعديل
            mutable_data = request.data.copy()
            mutable_data['payment_type'] = 'electronic'
            mutable_data['transaction_code'] = transaction_id
            request._full_data = mutable_data
            
            settle_view = SettlePaymentView()
            return settle_view.post(request)
            
        # 4. إذا لم ينجح التحقق الآلي (مرفوض أو غير متاح)، نُبقي المعاملة بحالة pending
        # ونُرجع نجاح الطلب ليتم إظهاره كـ "قيد المراجعة" للمستخدم.
        return Response({
            'success': True,
            'message': 'تم استلام طلب السداد وهو الآن قيد المراجعة اليدوية من قبل الإدارة',
            'data': {
                'transaction_id': transaction.transaction_id,
                'status': 'pending'
            }
        })

class SettlePaymentView(APIView):
    """
    نقطة النهاية المسؤولة عن معالجة السداد واتخاذ قرار إعادة التوصيل.
    تستقبل: room_id, amount, payment_type.
    """
    permission_classes = [IsAuthenticatedCustom, IsAdminOrAccountantOrCashier]

    def post(self, request):
        from decimal import Decimal, InvalidOperation
        
        room_id = request.data.get('room_id')
        amount_raw = request.data.get('amount')
        payment_type = request.data.get('payment_type')

        # 1. التحقق من صحة المعطيات الأساسية
        if not room_id:
            raise ValidationError("معرف الغرفة (room_id) مطلوب")
        if amount_raw is None:
            raise ValidationError("مبلغ السداد (amount) مطلوب")
        if not payment_type:
            raise ValidationError("نوع السداد (payment_type) مطلوب")

        if payment_type not in ['cash', 'electronic']:
            raise ValidationError("نوع السداد غير صالح. يجب أن يكون cash أو electronic")

        if request.user.role == 'cashier' and payment_type != 'cash':
            from .exceptions import PermissionDeniedError
            raise PermissionDeniedError("أمين المكتب مسموح له فقط بالسداد النقدي")

        try:
            amount = Decimal(str(amount_raw))
        except (ValueError, InvalidOperation):
            raise ValidationError("مبلغ السداد غير صالح")

        if amount <= Decimal(0):
            raise ValidationError("مبلغ السداد يجب أن يكون أكبر من الصفر")

        # 2. التحقق من وجود الغرفة
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            raise NotFoundError("الغرفة المطلوبة غير موجودة")

        # 3. إذا كان السداد إلكترونياً، التحقق من كود المعاملة
        if payment_type == 'electronic':
            transaction_code = request.data.get('transaction_code')
            if not transaction_code:
                raise ValidationError("كود المعاملة (transaction_code) مطلوب للسداد الإلكتروني")
            
            from .models import Transaction
            from .exceptions import InvalidTransactionError
            try:
                txn = Transaction.objects.get(transaction_id=transaction_code, verification_status='verified')
            except Transaction.DoesNotExist:
                raise InvalidTransactionError()

        # 4. جلب الفواتير غير المدفوعة للغرفة لحساب إجمالي المديونية
        unpaid_invoices = Invoice.objects.filter(room=room).exclude(status='paid').order_by('created_at')
        total_debt = sum((inv.final_amount or Decimal(0)) + (inv.overdue_fine or Decimal(0)) for inv in unpaid_invoices)

        # 5. خصم المبلغ وتوزيعه بنظام FIFO على الفواتير المستحقة
        remaining_payment = amount
        for inv in unpaid_invoices:
            if remaining_payment <= Decimal(0):
                break

            inv_fine = inv.overdue_fine or Decimal(0)
            inv_amount = inv.final_amount or Decimal(0)
            inv_total = inv_fine + inv_amount

            if remaining_payment >= inv_total:
                # تسوية الفاتورة كاملة (القيمة والغرامة)
                remaining_payment -= inv_total
                inv.status = 'paid'
                inv.paid_at = timezone.now()
                inv.save()
            else:
                # تسوية جزئية للفاتورة
                # نخصم من غرامة التأخير أولاً
                if inv_fine > Decimal(0):
                    if remaining_payment >= inv_fine:
                        remaining_payment -= inv_fine
                        inv.overdue_fine = Decimal(0)
                    else:
                        inv.overdue_fine -= remaining_payment
                        remaining_payment = Decimal(0)

                # خصم ما تبقى من قيمة الاستهلاك الأساسية للفاتورة
                if remaining_payment > Decimal(0):
                    inv.final_amount -= remaining_payment
                    remaining_payment = Decimal(0)

                inv.save()

        # 6. حساب المديونية المتبقية
        remaining_debt = max(total_debt - amount, Decimal(0))

        # 6.5. التحقق من خطة التقسيط وتسديد الأقساط
        from .models import InstallmentPlan
        active_plan = InstallmentPlan.objects.filter(room=room, status='active').first()
        if active_plan:
            plan_payment_pool = amount
            pending_installments = active_plan.payments.filter(status__in=['pending', 'overdue']).order_by('due_date')
            
            for inst in pending_installments:
                if plan_payment_pool <= Decimal(0):
                    break
                
                if plan_payment_pool >= inst.remaining_amount:
                    plan_payment_pool -= inst.remaining_amount
                    inst.remaining_amount = Decimal(0)
                    inst.status = 'paid'
                    inst.paid_at = timezone.now()
                    inst.save()
                else:
                    inst.remaining_amount -= plan_payment_pool
                    plan_payment_pool = Decimal(0)
                    inst.save()
            
            if not active_plan.payments.exclude(status='paid').exists():
                active_plan.status = 'completed'
                active_plan.save()

        # 7. جلب حد التوصيل واتخاذ القرار
        settings_obj = SystemSettings.get_settings()
        reconnect_threshold = settings_obj.reconnect_debt_threshold

        service_reconnected   = False
        meter_command_warning = None

        if remaining_debt <= reconnect_threshold or active_plan:
            try:
                MeterCommandService.connect(room_id)
                service_reconnected = True
            except MeterCommandError as meter_err:
                # فشل توصيل العداد لا يُوقف عملية السداد —
                # السداد تمّ بنجاح، لكن نُعيد تحذيراً في الرد.
                meter_command_warning = str(meter_err.detail)

        # 8. صياغة رد الاستجابة
        response_data = {
            "total_debt_before": float(total_debt),
            "amount_paid": float(amount),
            "remaining_debt": float(remaining_debt),
            "reconnect_threshold": float(reconnect_threshold),
            "service_reconnected": service_reconnected,
        }
        if meter_command_warning:
            response_data["meter_warning"] = meter_command_warning

        from .services.audit_service import AuditLogger
        AuditLogger.log(
            actor=request.user,
            action_type='settle_payment',
            target_model='Room',
            target_id=str(room.id),
            description=f"تم سداد مبلغ {amount} ريال ({payment_type})",
            metadata={
                'amount': float(amount),
                'payment_type': payment_type,
                'remaining_debt': float(remaining_debt),
                'reconnected': service_reconnected,
                'decision_path': 'installment_plan' if active_plan else 'threshold'
            }
        )

        if service_reconnected:
            return Response({
                "success": True,
                "message": "تمت معالجة السداد بنجاح وإعادة توصيل الخدمة للغرفة.",
                "data": response_data
            }, status=status.HTTP_200_OK)
        else:
            required_amount = remaining_debt - reconnect_threshold
            return Response({
                "success": True,
                "message": f"تم خصم السداد. المديونية المتبقية ({float(remaining_debt)} ريال) أكبر من حد التوصيل ({float(reconnect_threshold)} ريال). يرجى سداد {float(required_amount)} ريال إضافية لإعادة التوصيل.",
                "data": response_data
            }, status=status.HTTP_200_OK)


class CreateInstallmentPlanView(APIView):
    permission_classes = [IsAuthenticatedCustom, IsAdminOrAccountant]

    def post(self, request):
        from decimal import Decimal
        from .models import InstallmentPlan, InstallmentPayment
        from .exceptions import ActiveInstallmentPlanExistsError
        
        room_id = request.data.get('room_id')
        number_of_installments = int(request.data.get('number_of_installments', 3))
        interval_days = int(request.data.get('interval_days', 14))

        if not room_id:
            raise ValidationError("معرف الغرفة (room_id) مطلوب")
        if number_of_installments < 1:
            raise ValidationError("عدد الأقساط يجب أن يكون أكبر من الصفر")
        if interval_days < 1:
            raise ValidationError("الفاصل الزمني بين الأقساط يجب أن يكون يوماً واحداً على الأقل")

        room = Room.objects.get(id=room_id)

        # التحقق من عدم وجود خطة نشطة
        if InstallmentPlan.objects.filter(room=room, status='active').exists():
            raise ActiveInstallmentPlanExistsError()

        # حساب المديونية الفعلية
        unpaid_invoices = Invoice.objects.filter(room=room).exclude(status='paid')
        total_debt = sum((inv.final_amount or Decimal(0)) + (inv.overdue_fine or Decimal(0)) for inv in unpaid_invoices)

        if total_debt <= Decimal(0):
            raise ValidationError("لا توجد مديونية على هذه الغرفة لتقسيطها")

        # إنشاء الخطة
        plan = InstallmentPlan.objects.create(
            room=room,
            total_amount=total_debt,
            number_of_installments=number_of_installments,
            created_by=request.user
        )

        # تقسيم المبلغ
        installment_amount = round(total_debt / Decimal(number_of_installments), 2)
        remainder = total_debt - (installment_amount * number_of_installments)

        current_date = timezone.now().date()
        for i in range(number_of_installments):
            amount_for_this = installment_amount
            if i == number_of_installments - 1:
                amount_for_this += remainder
            
            due_date = current_date + timedelta(days=(i+1)*interval_days)
            InstallmentPayment.objects.create(
                plan=plan,
                due_date=due_date,
                amount=amount_for_this,
                remaining_amount=amount_for_this
            )

        # توصيل الخدمة فوراً
        try:
            MeterCommandService.connect(room.id)
        except MeterCommandError:
            pass

        from .services.audit_service import AuditLogger
        AuditLogger.log(
            actor=request.user,
            action_type='installment_plan_created',
            target_model='InstallmentPlan',
            target_id=str(plan.id),
            description=f"تم إنشاء خطة تقسيط للغرفة بمبلغ {total_debt}",
            metadata={
                'total_amount': float(total_debt),
                'installments': number_of_installments,
                'room_id': room.id
            }
        )

        return Response({
            "success": True,
            "message": "تم إنشاء خطة التقسيط وإعادة توصيل الخدمة بنجاح",
            "data": {
                "plan_id": plan.id,
                "total_amount": float(total_debt),
                "installments": number_of_installments
            }
        }, status=status.HTTP_201_CREATED)


class ManualMeterActionView(APIView):
    permission_classes = [IsAuthenticatedCustom, IsAdminUser]

    def post(self, request):
        from .models import ManualMeterAction
        from .exceptions import InvalidManualActionReasonError

        room_id = request.data.get('room_id')
        action_type = request.data.get('action_type')
        reason = request.data.get('reason', '').strip()

        if not room_id or action_type not in ['connect', 'disconnect']:
            raise ValidationError("البيانات المطلوبة (room_id, action_type) غير صحيحة")

        if len(reason) < 10:
            raise InvalidManualActionReasonError()

        room = Room.objects.get(id=room_id)

        # حفظ الإجراء المبرر
        action_record = ManualMeterAction.objects.create(
            room=room,
            action_type=action_type,
            reason=reason,
            performed_by=request.user
        )

        # التنفيذ الفعلي
        if action_type == 'connect':
            MeterCommandService.connect(room.id)
        else:
            MeterCommandService.disconnect(room.id)

        from .services.audit_service import AuditLogger
        AuditLogger.log(
            actor=request.user,
            action_type='manual_meter_action',
            target_model='Room',
            target_id=str(room.id),
            description=f"إجراء يدوي للعداد: {action_record.get_action_type_display()} بسبب: {reason}"
        )

        return Response({
            "success": True,
            "message": f"تم تنفيذ إجراء {action_record.get_action_type_display()} بنجاح"
        })

    def get(self, request):
        from .models import ManualMeterAction
        room_id = request.query_params.get('room_id')
        if not room_id:
            raise ValidationError("معرف الغرفة (room_id) مطلوب لعرض السجل")

        actions = ManualMeterAction.objects.filter(room_id=room_id).order_by('-performed_at')
        data = [{
            "id": a.id,
            "action_type": a.action_type,
            "reason": a.reason,
            "performed_by": a.performed_by.username if a.performed_by else None,
            "performed_at": a.performed_at
        } for a in actions]

        return Response({"success": True, "data": data})


class AuditLogListView(APIView):
    """
    سجل التدقيق المركزي (Admin Only)
    """
    permission_classes = [IsAuthenticatedCustom, IsAdminUser]

    def get(self, request):
        from .models import AuditLog
        from .serializers import AuditLogSerializer
        from django.utils.dateparse import parse_date

        queryset = AuditLog.objects.all()

        actor_id = request.query_params.get('actor')
        if actor_id:
            queryset = queryset.filter(actor_id=actor_id)

        action_type = request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)

        target_model = request.query_params.get('target_model')
        if target_model:
            queryset = queryset.filter(target_model=target_model)

        target_id = request.query_params.get('target_id')
        if target_id:
            queryset = queryset.filter(target_id=target_id)

        start_date = request.query_params.get('start_date')
        if start_date:
            parsed_start = parse_date(start_date)
            if parsed_start:
                queryset = queryset.filter(created_at__date__gte=parsed_start)

        end_date = request.query_params.get('end_date')
        if end_date:
            parsed_end = parse_date(end_date)
            if parsed_end:
                queryset = queryset.filter(created_at__date__lte=parsed_end)

        serializer = AuditLogSerializer(queryset, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        })
