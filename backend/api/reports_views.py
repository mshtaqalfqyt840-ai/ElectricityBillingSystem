from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum
from .models import ArchiveReport, Invoice
from .serializers import ArchiveReportSerializer
import datetime

class ArchiveReportViewSet(viewsets.ModelViewSet):
    queryset = ArchiveReport.objects.all()
    serializer_class = ArchiveReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def current_summary(self, request):
        """
        Calculates the current un-archived totals to display on the dashboard
        before the user clicks 'Archive'. 
        It aggregates all Invoices that haven't been archived yet.
        """
        # For simplicity, we can aggregate all Invoices that were created since the last archive date.
        last_archive = ArchiveReport.objects.order_by('-created_at').first()
        
        invoices = Invoice.objects.all()
        if last_archive:
            invoices = invoices.filter(created_at__gt=last_archive.created_at)

        total_consumption = invoices.aggregate(Sum('consumption'))['consumption__sum'] or 0.0
        total_due = invoices.aggregate(Sum('final_amount'))['final_amount__sum'] or 0.0
        total_paid = invoices.filter(status='paid').aggregate(Sum('final_amount'))['final_amount__sum'] or 0.0
        remaining_balance = total_due - total_paid

        # Service fees (assuming service_fee from SystemSettings is applied to each invoice)
        # We can just sum the overdrive_fine if it was used for service fees, or we can just fetch it.
        # Based on previous logic, we can just estimate or leave it as 0 to be filled manually.

        data = {
            'total_kwh_consumption': total_consumption,
            'total_amount_due': total_due,
            'total_service_fees': 0, # Will be filled manually or derived if needed
            'total_paid': total_paid,
            'remaining_balance': remaining_balance,
            'net_balance': total_paid, # Example calculation
        }
        return Response(data)

    def perform_create(self, serializer):
        serializer.save(archived_by=self.request.user)
