"""
api/tasks.py
المهام المجدولة (Scheduled Tasks) باستخدام APScheduler.

send_critical_warnings():
    تعمل كل ساعة وتبحث عن الفواتير غير المسددة التي:
    - لم يُرسل لها اشعار حرج من قبل (warning_sent=False)
    - يتبقى على payment_deadline الخاص بها 5 ساعات او اقل

    عند العثور على اي فاتورة مطابقة:
    1. تستدعي NotificationService.send_critical_warning(invoice)
    2. تحدّث invoice.warning_sent = True لمنع التكرار
"""
import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

# حد الانذار الحرج بالساعات — يتوافق مع القيمة المعروضة في PaymentCountdown
CRITICAL_THRESHOLD_HOURS = 5


def send_critical_warnings():
    """
    المهمة المجدولة الرئيسية: ترسل انذار حرج لكل فاتورة غير مسددة
    تبقى على مهلة سدادها 5 ساعات او اقل.

    يتم استدعاؤها تلقائيا كل ساعة عبر APScheduler (مسجّلة في apps.py).
    """
    # الاستيراد هنا (lazy) لتجنب مشاكل circular import عند بدء تشغيل Django
    from .models import Invoice, SystemSettings
    from .services import NotificationService

    logger.info("[Task:send_critical_warnings] Starting hourly check...")

    settings_obj       = SystemSettings.get_settings()
    deadline_hours     = settings_obj.payment_deadline_hours
    now                = timezone.now()
    critical_threshold = timedelta(hours=CRITICAL_THRESHOLD_HOURS)

    # جلب الفواتير غير المسددة التي لم يُرسل لها انذار بعد
    unpaid_invoices = (
        Invoice.objects
        .exclude(status="paid")
        .filter(warning_sent=False)
        .select_related("room")
    )

    sent_count    = 0
    skipped_count = 0

    for invoice in unpaid_invoices:
        payment_deadline = invoice.created_at + timedelta(hours=deadline_hours)
        time_remaining   = payment_deadline - now

        if timedelta(0) < time_remaining <= critical_threshold:
            # يتبقى اقل من 5 ساعات ولم يُرسل اشعار -> ارسل
            try:
                NotificationService.send_critical_warning(invoice)
                invoice.warning_sent = True
                invoice.save(update_fields=["warning_sent"])
                sent_count += 1
                
                from .services.audit_service import AuditLogger
                AuditLogger.log(
                    actor=None,
                    action_type='critical_warning_sent',
                    target_model='Invoice',
                    target_id=str(invoice.id),
                    description=f"إرسال إنذار حرج للفاتورة {invoice.id} (الغرفة {invoice.room.qr_code})"
                )
            except Exception as exc:
                logger.error(
                    "[Task:send_critical_warnings] Failed for invoice_id=%s: %s",
                    invoice.id, exc,
                )
        else:
            skipped_count += 1

    logger.info(
        "[Task:send_critical_warnings] Done — sent=%d skipped=%d",
        sent_count, skipped_count,
    )


def auto_disconnect_overdue_invoices():
    """
    المهمة المجدولة الثانية: تبحث عن الفواتير التي تجاوزت مهلة السداد
    وحالة عدادها موصّل (connected)، فتقوم بفصله وتسجيل إشعار.
    """
    from .models import Invoice, SystemSettings
    from .services.notification_service import NotificationService
    from .services.meter_service import MeterCommandService

    logger.info("[Task:auto_disconnect_overdue] Starting hourly check...")

    settings_obj   = SystemSettings.get_settings()
    deadline_hours = settings_obj.payment_deadline_hours
    now            = timezone.now()

    # جلب الفواتير غير المسددة التي تخطت مهلة السداد وعدادها موصّل
    unpaid_invoices = (
        Invoice.objects
        .exclude(status="paid")
        .select_related("room", "room__meter")
    )

    disconnected_count = 0
    skipped_count      = 0

    for invoice in unpaid_invoices:
        payment_deadline = invoice.created_at + timedelta(hours=deadline_hours)
        
        # إذا تجاوز الوقت الحالي مهلة السداد
        if now > payment_deadline:
            # التحقق إذا كان العداد موصّل
            if hasattr(invoice.room, 'meter') and invoice.room.meter.connection_status == 'connected':
                try:
                    # فصل العداد
                    MeterCommandService.disconnect(invoice.room.id)
                    # تسجيل إشعار الفصل
                    NotificationService.send_auto_disconnect(invoice)
                    disconnected_count += 1

                    from .services.audit_service import AuditLogger
                    AuditLogger.log(
                        actor=None,
                        action_type='auto_disconnect',
                        target_model='Room',
                        target_id=str(invoice.room.id),
                        description=f"تم فصل العداد آلياً لتجاوز مهلة السداد للفاتورة {invoice.id}"
                    )
                except Exception as exc:
                    logger.error(
                        "[Task:auto_disconnect_overdue] Failed for invoice_id=%s: %s",
                        invoice.id, exc,
                    )
            else:
                skipped_count += 1
        else:
            skipped_count += 1

    logger.info(
        "[Task:auto_disconnect_overdue] Done — disconnected=%d skipped=%d",
        disconnected_count, skipped_count,
    )


def check_overdue_installments():
    """
    مهمة مجدولة: تفحص الأقساط التي تجاوزت تاريخ استحقاقها ولم تُسدد وتغير حالتها إلى overdue.
    إذا بلغ عدد الأقساط المتأخرة قسطين، يتم تغيير الخطة بأكملها إلى defaulted ويُفصل العداد.
    """
    from .models import InstallmentPayment, InstallmentPlan
    from .services.meter_service import MeterCommandService
    from django.utils import timezone

    logger.info("[Task:check_overdue_installments] Starting daily check...")
    today = timezone.now().date()

    # تحديث الأقساط إلى overdue
    overdue_payments = InstallmentPayment.objects.filter(
        status='pending',
        due_date__lt=today
    )
    updated_count = overdue_payments.update(status='overdue')

    # فحص الخطط النشطة لمعرفة المتعثر منها
    active_plans = InstallmentPlan.objects.filter(status='active')
    defaulted_count = 0

    for plan in active_plans:
        overdue_count = plan.payments.filter(status='overdue').count()
        if overdue_count >= 2:
            plan.status = 'defaulted'
            plan.save(update_fields=['status'])
            
            # محاولة فصل التيار
            try:
                MeterCommandService.disconnect(plan.room.id)
                defaulted_count += 1
            except Exception as exc:
                logger.error(
                    "[Task:check_overdue_installments] Failed to disconnect room_id=%s for defaulted plan_id=%s: %s",
                    plan.room.id, plan.id, exc
                )

    logger.info(
        "[Task:check_overdue_installments] Done — updated_payments=%d, defaulted_plans=%d",
        updated_count, defaulted_count
    )
