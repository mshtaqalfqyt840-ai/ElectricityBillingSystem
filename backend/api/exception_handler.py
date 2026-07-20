"""
api/exception_handler.py
مكافئ errorHandler.js — Custom DRF Exception Handler المركزي
يُسجَّل في settings.py تحت: REST_FRAMEWORK['EXCEPTION_HANDLER']
"""
import os
import logging
from rest_framework.views import exception_handler as drf_default_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError

from .exceptions import AppError, OverdueInvoiceError

logger = logging.getLogger(__name__)

# ── خرائط أكواد أخطاء PostgreSQL إلى رسائل عربية مفهومة ──
POSTGRES_ERROR_MESSAGES = {
    '23505': 'البيانات موجودة مسبقاً، يرجى استخدام قيمة مختلفة',           # unique violation
    '23503': 'لا يمكن تنفيذ العملية لأن البيانات المرتبطة غير موجودة',      # foreign key violation
    '23502': 'يوجد حقل إجباري لم يتم تعبئته',                               # not-null violation
    '22001': 'القيمة المدخلة تتجاوز الحد الأقصى المسموح به',                # string_data_right_truncation
    '22003': 'القيمة الرقمية خارج النطاق المسموح به',                        # numeric_value_out_of_range
}


def _handle_integrity_error(exc: IntegrityError) -> tuple[str, int]:
    """استخراج كود PostgreSQL وترجمته لرسالة عربية"""
    # psycopg2 يضع كود الخطأ في pgcode
    pg_code = getattr(exc.__cause__, 'pgcode', None)
    if pg_code and pg_code in POSTGRES_ERROR_MESSAGES:
        return POSTGRES_ERROR_MESSAGES[pg_code], status.HTTP_409_CONFLICT
    # fallback
    return 'خطأ في قاعدة البيانات، يرجى التحقق من البيانات المدخلة', status.HTTP_400_BAD_REQUEST


def _is_development() -> bool:
    """هل نحن في بيئة التطوير؟"""
    return os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')


def custom_exception_handler(exc, context):
    """
    مكافئ errorHandler.js (4 معاملات: err, req, res, next)
    يعالج:
      أ) AppError المخصصة → يستخدم statusCode و message منها مباشرة
      ب) أخطاء PostgreSQL (IntegrityError) → رسائل عربية مفهومة
      ج) أخطاء JWT → 401 (يتعامل معها custom authentication مسبقاً لكن نضيف fallback)
      د) Http404 من Django → 404 موحّد
      هـ) PermissionDenied من Django → 403 موحّد
      و) أي خطأ غير متوقع → 500 مع رسالة عامة (بدون تفاصيل داخلية في production)

    شكل الرد الموحد:
      { success: false, status: "fail"|"error", message: "...", ...(stack في dev فقط) }
    """
    is_dev = _is_development()
    request = context.get('request')

    # ── أ-1) OverdueInvoiceError — فاتورة متأخرة (تُعاد غرامتها في الرد) ──
    if isinstance(exc, OverdueInvoiceError):
        response_data = {
            'success': False,
            'status': exc.status,
            'message': str(exc.detail),
            'overdue_fine': exc.overdue_fine,
        }
        if is_dev:
            import traceback
            response_data['stack'] = traceback.format_exc()
        return Response(response_data, status=exc.status_code)

    # ── أ-2) AppError المخصصة (عام) ──
    if isinstance(exc, AppError):
        response_data = {
            'success': False,
            'status': exc.status,
            'message': str(exc.detail),
        }
        if is_dev:
            import traceback
            response_data['stack'] = traceback.format_exc()
        return Response(response_data, status=exc.status_code)

    # ── ب) أخطاء قاعدة البيانات PostgreSQL ──
    if isinstance(exc, IntegrityError):
        message, status_code = _handle_integrity_error(exc)
        response_data = {
            'success': False,
            'status': 'fail',
            'message': message,
        }
        if is_dev:
            response_data['detail'] = str(exc)
        logger.warning(f"IntegrityError [{request.method} {request.path}]: {exc}")
        return Response(response_data, status=status_code)

    # ── ج) Http404 من Django (مثل: get_object_or_404) ──
    if isinstance(exc, Http404):
        return Response({
            'success': False,
            'status': 'fail',
            'message': str(exc) if str(exc) else 'المورد المطلوب غير موجود',
        }, status=status.HTTP_404_NOT_FOUND)

    # ── د) PermissionDenied من Django ──
    if isinstance(exc, PermissionDenied):
        return Response({
            'success': False,
            'status': 'fail',
            'message': 'ليس لديك صلاحية للوصول لهذا المورد',
        }, status=status.HTTP_403_FORBIDDEN)

    # ── هـ) تحويل أخطاء DRF الافتراضية للشكل الموحّد ──
    drf_response = drf_default_handler(exc, context)
    if drf_response is not None:
        original_data = drf_response.data
        # استخراج رسالة موحدة من بنية DRF المختلفة
        if isinstance(original_data, dict):
            message = original_data.get('detail', str(original_data))
        elif isinstance(original_data, list):
            message = str(original_data[0]) if original_data else 'خطأ في البيانات'
        else:
            message = str(original_data)

        # تحديد status بناءً على status code
        http_status = drf_response.status_code
        status_label = 'fail' if http_status < 500 else 'error'

        unified_data = {
            'success': False,
            'status': status_label,
            'message': message,
        }
        if is_dev and http_status >= 500:
            import traceback
            unified_data['stack'] = traceback.format_exc()

        drf_response.data = unified_data
        return drf_response

    # ── و) أي خطأ غير متوقع (500) ──
    logger.error(
        f"Unexpected error [{request.method if request else 'N/A'} "
        f"{request.path if request else 'N/A'}]: {type(exc).__name__}: {exc}",
        exc_info=True
    )
    response_data = {
        'success': False,
        'status': 'error',
        'message': 'حدث خطأ في الخادم',  # لا نُظهر تفاصيل داخلية في production
    }
    if is_dev:
        import traceback
        response_data['detail'] = f"{type(exc).__name__}: {str(exc)}"
        response_data['stack'] = traceback.format_exc()

    return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
