import os
import django
from datetime import datetime
from django.utils import timezone
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Building, Room, Invoice
from api.services.financial_report_service import FinancialReportService

# 1. Setup
Building.objects.all().delete()
Room.objects.all().delete()
Invoice.objects.all().delete()

building = Building.objects.create(name="Test Building", code="T")
room = Room.objects.create(room_number=101, building=building, qr_code="QR101")

# 2. Create Invoice in July
# We need to bypass auto_now_add for created_at, so we update it after creation
invoice = Invoice.objects.create(
    room=room,
    status='approved',
    consumption=Decimal('100.00'),
    unit_price=Decimal('0.15'),
    total_amount=Decimal('15.00'),
    final_amount=Decimal('15.00'),
)
# Force created_at to July 15th
Invoice.objects.filter(id=invoice.id).update(created_at=timezone.make_aware(datetime(2026, 7, 15, 12, 0, 0)))

# 3. Generate Report for July BEFORE payment
report_before = FinancialReportService.generate('2026-07-01', '2026-07-31')
outstanding_before = report_before['summary']['total_outstanding']
print(f"Outstanding debt BEFORE payment (July Report): {outstanding_before}")

# 4. Simulate payment in August
invoice.refresh_from_db()
invoice.status = 'paid'
invoice.paid_at = timezone.make_aware(datetime(2026, 8, 2, 10, 0, 0))
invoice.save()

# 5. Generate Report for July AFTER payment (Should be the same)
report_after = FinancialReportService.generate('2026-07-01', '2026-07-31')
outstanding_after = report_after['summary']['total_outstanding']
print(f"Outstanding debt AFTER payment in August (July Report): {outstanding_after}")

if outstanding_before == outstanding_after and outstanding_before == 15.0:
    print("TEST PASSED: The outstanding debt remained constant despite future payment.")
else:
    print("❌ TEST FAILED: The outstanding debt changed or was incorrect.")
