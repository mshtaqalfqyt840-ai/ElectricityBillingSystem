from decimal import Decimal
from django.db.models import Sum
from django.utils.dateparse import parse_date
from datetime import datetime, time
from django.utils.timezone import make_aware
from api.models import Invoice, Building

class FinancialReportService:
    @staticmethod
    def generate(start_date_str, end_date_str, building_id=None):
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        
        if not start_date or not end_date:
            raise ValueError("يجب توفير تاريخ بداية ونهاية صحيحين.")

        start_dt = make_aware(datetime.combine(start_date, time.min))
        end_dt = make_aware(datetime.combine(end_date, time.max))

        # 1. الاستهلاك والفواتير الصادرة ضمن الفترة
        invoices_in_period = Invoice.objects.filter(created_at__range=(start_dt, end_dt))
        if building_id:
            invoices_in_period = invoices_in_period.filter(room__building_id=building_id)

        # 2. المبالغ المحصّلة فعلياً ضمن الفترة (حسب paid_at)
        paid_in_period = Invoice.objects.filter(status='paid', paid_at__range=(start_dt, end_dt))
        if building_id:
            paid_in_period = paid_in_period.filter(room__building_id=building_id)

        # 3. المديونيات المعلّقة كما كانت في نهاية الفترة end_date
        # الفواتير التي صدرت قبل أو خلال الفترة (<= end_dt)
        # ولم تسدد أبداً، أو سُددت بعد تاريخ end_dt
        outstanding_invoices = Invoice.objects.filter(created_at__lte=end_dt).exclude(
            status='paid', paid_at__lte=end_dt
        )
        if building_id:
            outstanding_invoices = outstanding_invoices.filter(room__building_id=building_id)

        # حسابات الملخص العام
        total_consumption = invoices_in_period.aggregate(Sum('consumption'))['consumption__sum'] or Decimal(0)
        total_collected = paid_in_period.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal(0)
        
        # المديونيات = القيمة النهائية + الغرامات
        total_outstanding_amount = outstanding_invoices.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal(0)
        total_outstanding_fine = outstanding_invoices.aggregate(Sum('overdue_fine'))['overdue_fine__sum'] or Decimal(0)
        total_outstanding = total_outstanding_amount + total_outstanding_fine

        issued_count = invoices_in_period.count()
        paid_count = paid_in_period.count()
        overdue_count = outstanding_invoices.filter(is_overdue=True).count()

        summary = {
            'total_consumption': float(total_consumption),
            'total_collected': float(total_collected),
            'total_outstanding': float(total_outstanding),
            'issued_count': issued_count,
            'paid_count': paid_count,
            'overdue_count': overdue_count
        }

        # التفصيل حسب المبنى (إذا لم يُحدد مبنى معين)
        buildings_detail = []
        if not building_id:
            buildings = Building.objects.all()
            for b in buildings:
                b_invoices = invoices_in_period.filter(room__building=b)
                b_paid = paid_in_period.filter(room__building=b)
                b_outstanding = outstanding_invoices.filter(room__building=b)

                b_cons = b_invoices.aggregate(Sum('consumption'))['consumption__sum'] or Decimal(0)
                b_coll = b_paid.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal(0)
                
                b_out_amt = b_outstanding.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal(0)
                b_out_fine = b_outstanding.aggregate(Sum('overdue_fine'))['overdue_fine__sum'] or Decimal(0)
                b_out = b_out_amt + b_out_fine

                buildings_detail.append({
                    'building_id': b.id,
                    'building_name': b.name,
                    'total_consumption': float(b_cons),
                    'total_collected': float(b_coll),
                    'total_outstanding': float(b_out),
                    'issued_count': b_invoices.count(),
                    'paid_count': b_paid.count(),
                    'overdue_count': b_outstanding.filter(is_overdue=True).count(),
                })

        return {
            'period': {
                'start': start_date_str,
                'end': end_date_str
            },
            'building_id': building_id,
            'summary': summary,
            'buildings_detail': buildings_detail
        }
