from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    BuildingViewSet, RoomViewSet, StudentViewSet,
    UserViewSet, InvoiceViewSet, SystemSettingsView, SettlePaymentView,
    VerifyTransactionView, ComplaintViewSet, PublicRoomInvoiceView,
    CreateInstallmentPlanView, ManualMeterActionView, AuditLogListView, PingView
)
from .views_auth import LoginView
from .views_reports import FinancialReportView
from .reports_views import ArchiveReportViewSet

router = DefaultRouter()
router.register(r'buildings', BuildingViewSet)
router.register(r'rooms', RoomViewSet)
router.register(r'students', StudentViewSet)
router.register(r'users', UserViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'complaints', ComplaintViewSet, basename='complaint')
router.register(r'archive-reports', ArchiveReportViewSet, basename='archivereport')

urlpatterns = [
    path('', include(router.urls)),
    path('ping/', PingView.as_view(), name='ping'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('settings/', SystemSettingsView.as_view(), name='system-settings'),
    path('verify-transaction/', VerifyTransactionView.as_view(), name='verify-transaction'),
    path('settle-payment/', SettlePaymentView.as_view(), name='settle-payment'),
    path('public/room/<str:qr_code>/invoice/', PublicRoomInvoiceView.as_view(), name='public-room-invoice'),
    path('installment-plans/', CreateInstallmentPlanView.as_view(), name='create-installment-plan'),
    path('manual-meter-action/', ManualMeterActionView.as_view(), name='manual-meter-action'),
    path('audit-logs/', AuditLogListView.as_view(), name='audit-logs'),
    path('reports/financial/', FinancialReportView.as_view(), name='financial-report'),
]
