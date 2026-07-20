from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from django.utils import timezone
from .models import User, Room, Building, Meter, Invoice, InstallmentPlan, InstallmentPayment, SystemSettings

class InstallmentPlanAndManualActionTests(APITestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create(username='admin_user', password_hash='hash', role='admin')
        self.accountant = User.objects.create(username='accountant_user', password_hash='hash', role='accountant')
        self.delegate = User.objects.create(username='delegate_user', password_hash='hash', role='delegate')
        
        # Create building, room, meter
        self.building = Building.objects.create(name='Building 1', code='B')
        self.room = Room.objects.create(room_number=101, building=self.building, qr_code='QR101')
        self.meter = Meter.objects.create(room=self.room, meter_serial='SN-001', connection_status='disconnected')
        
        # Ensure system settings exist
        SystemSettings.get_settings()

    def test_rbac_installment_plan_creation(self):
        """تأكد أن المندوب لا يستطيع إنشاء خطة تقسيط"""
        self.client.force_authenticate(user=self.delegate)
        response = self.client.post('/api/installment-plans/', {
            'room_id': self.room.id,
            'number_of_installments': 3
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rbac_manual_meter_action(self):
        """تأكد أن المحاسب لا يستطيع القيام بفصل/توصيل يدوي"""
        self.client.force_authenticate(user=self.accountant)
        response = self.client.post('/api/manual-meter-action/', {
            'room_id': self.room.id,
            'action_type': 'connect',
            'reason': 'هذا سبب كافٍ للفصل اليدوي'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # المشرف يستطيع
        self.client.force_authenticate(user=self.admin)
        response_admin = self.client.post('/api/manual-meter-action/', {
            'room_id': self.room.id,
            'action_type': 'connect',
            'reason': 'هذا سبب كافٍ للفصل اليدوي'
        })
        self.assertEqual(response_admin.status_code, status.HTTP_200_OK)

    def test_installment_plan_partial_payment_scenario(self):
        """
        تأكد من السيناريو المعقد: 
        1. دين كلي > 300
        2. إنشاء خطة تقسيط -> العداد يتصل
        3. سداد جزء من القسط الأول
        4. الدين الكلي ما يزال > 300 ولكن العداد يبقى متصلاً لوجود خطة نشطة
        """
        # 1. إنشاء مديونية كبيرة (1000 ريال)
        Invoice.objects.create(
            room=self.room,
            final_amount=Decimal('1000.00'),
            status='approved'
        )
        
        # 2. إنشاء خطة تقسيط (3 أقساط كل 14 يوم) - يحق للمحاسب
        self.client.force_authenticate(user=self.accountant)
        response = self.client.post('/api/installment-plans/', {
            'room_id': self.room.id,
            'number_of_installments': 3,
            'interval_days': 14
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        plan = InstallmentPlan.objects.get(room=self.room, status='active')
        self.assertEqual(plan.total_amount, Decimal('1000.00'))
        
        # التأكد أن العداد قد أرسل له أمر التوصيل (Mock updates connection_status in DB)
        self.meter.refresh_from_db()
        self.assertEqual(self.meter.connection_status, 'connected')

        first_installment = plan.payments.order_by('due_date').first()
        self.assertEqual(first_installment.amount, Decimal('333.33'))
        
        # 3. سداد جزئي (100 ريال)
        settle_response = self.client.post('/api/settle-payment/', {
            'room_id': self.room.id,
            'amount': '100.00',
            'payment_type': 'cash'
        })
        self.assertEqual(settle_response.status_code, status.HTTP_200_OK)
        
        # 4. التأكد من النتيجة
        self.assertTrue(settle_response.data['data']['service_reconnected'])
        self.assertEqual(settle_response.data['data']['remaining_debt'], 900.0) # > 300 threshold
        
        # التأكد من خصم الـ 100 من القسط الأول
        first_installment.refresh_from_db()
        self.assertEqual(first_installment.remaining_amount, Decimal('233.33'))
        self.assertEqual(first_installment.status, 'pending')
