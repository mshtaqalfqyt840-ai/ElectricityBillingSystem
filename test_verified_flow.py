import os
import django
import sys
sys.path.append(r'c:\Users\hp\Desktop\ElectricityBillingSystem\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['PAYMENT_GATEWAY_MOCK_MODE'] = 'verified'

django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from api.views import VerifyTransactionView
from api.models import Room, Building, Transaction, User

def run_test():
    # 1. Setup Data
    user, _ = User.objects.get_or_create(username='test_admin', role='admin')
    
    building, _ = Building.objects.get_or_create(name='Test Building')
    room, _ = Room.objects.get_or_create(
        room_number='101', 
        building=building
    )
    
    # 1.5 Create Meter
    from api.models import Meter
    meter, _ = Meter.objects.get_or_create(room=room, meter_serial='M-TEST-123')
    meter.connection_status = 'disconnected'
    meter.save()
    
    # 2. Simulate pending invoice
    # Actually, SettlePaymentView will settle the invoice. We might need an invoice.
    # Let's just create a transaction and see if SettlePaymentView gets called.
    from api.models import Invoice
    invoice, _ = Invoice.objects.get_or_create(
        room=room, 
        total_amount=100.0, 
        status='pending'
    )
    # (Meter status is already set to disconnected)
    
    # 3. Create Request
    factory = APIRequestFactory()
    data = {
        'transaction_id': 'TXN-99991234',
        'wallet_provider': 'STC Pay',
        'room_id': room.id,
        'amount': '100.00'
    }
    from rest_framework.test import force_authenticate
    request = factory.post('/api/transactions/verify/', data, format='json')
    force_authenticate(request, user=user)

    # 4. Call View
    view = VerifyTransactionView.as_view()
    response = view(request)
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Data: {response.data}")
    
    # 5. Verify Database State
    txn = Transaction.objects.get(transaction_id='TXN-99991234')
    print(f"Transaction Status: {txn.verification_status}")
    
    invoice.refresh_from_db()
    print(f"Invoice Status: {invoice.status}")
    
    meter.refresh_from_db()
    print(f"Meter Connection Status: {meter.connection_status}")

if __name__ == '__main__':
    run_test()
