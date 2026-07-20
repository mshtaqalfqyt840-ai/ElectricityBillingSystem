"""
api/exceptions.py
مكافئ AppError.js — custom exception classes لنظام الفواتير الكهربائية
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class AppError(APIException):
    """
    Base custom exception — مكافئ class AppError(Error) في Node.js
    يوفر: status_code, status ('fail' أو 'error'), is_operational = True
    """
    is_operational = True

    def __init__(self, message: str, status_code: int = 400):
        self.status_code = status_code
        self.detail = message
        # 4xx = 'fail' | 5xx = 'error' (نفس المنطق في Node.js)
        self.status = 'fail' if status_code < 500 else 'error'
        super().__init__(detail=message)


# ── أخطاء جاهزة شائعة الاستخدام في المشروع ──

class NotFoundError(AppError):
    """المورد غير موجود — 404"""
    def __init__(self, message: str = "المورد المطلوب غير موجود"):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class PermissionDeniedError(AppError):
    """لا توجد صلاحية — 403"""
    def __init__(self, message: str = "ليس لديك صلاحية للوصول لهذا المورد"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class ValidationError(AppError):
    """خطأ في البيانات المدخلة — 400"""
    def __init__(self, message: str = "البيانات المدخلة غير صحيحة"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class UnauthorizedError(AppError):
    """غير مصرح له — 401"""
    def __init__(self, message: str = "يجب تسجيل الدخول أولاً"):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class ConflictError(AppError):
    """تعارض في البيانات (مثل: قيمة مكررة) — 409"""
    def __init__(self, message: str = "البيانات موجودة مسبقاً"):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class OverdueInvoiceError(AppError):
    """
    فاتورة تجاوزت مهلة السداد — 402 Payment Required.
    يحمل قيمة الغرامة المطبقة (overdue_fine) في جسم الاستثناء
    ليتمكن exception_handler من إرجاعها ضمن بيانات الرد.
    """
    def __init__(self, overdue_fine: float, message: str = None):
        self.overdue_fine = overdue_fine
        msg = message or (
            f"هذه الفاتورة تجاوزت مهلة السداد المحددة. "
            f"غرامة التأخير المطبقة: {overdue_fine} ريال. "
            f"يرجى التواصل مع المحاسب لتسوية المبلغ أولاً."
        )
        super().__init__(msg, status_code=status.HTTP_402_PAYMENT_REQUIRED)


class MeterCommandError(AppError):
    """
    فشل تنفيذ أمر على العداد الذكي (Timeout أو خطأ شبكة) — 503 Service Unavailable.
    يُطلق بعد استنفاد جميع المحاولات (max_retries) دون نجاح.
    يحمل: command ('connect'|'disconnect'), room_id, attempts لمساعدة الـ logs.
    """
    def __init__(
        self,
        command: str,
        room_id: int,
        attempts: int,
        message: str = None,
    ):
        self.command  = command
        self.room_id  = room_id
        self.attempts = attempts
        action_ar = 'التوصيل' if command == 'connect' else 'الفصل'
        msg = message or (
            f"تعذر تنفيذ أمر {action_ar}، سيُعاد المحاولة تلقائياً"
        )
        super().__init__(msg, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class InvalidTransactionError(AppError):
    """
    كود التحويل من المحفظة غير صحيح أو مستخدم مسبقاً — 400
    """
    def __init__(self, message: str = "الكود المدخل غير صحيح أو مستخدم سابقاً"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class ActiveInstallmentPlanExistsError(AppError):
    """خطة تقسيط نشطة موجودة بالفعل — 400"""
    def __init__(self, message: str = "توجد خطة تقسيط نشطة بالفعل لهذه الغرفة"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class InvalidManualActionReasonError(AppError):
    """سبب الفصل/التوصيل اليدوي غير صالح — 400"""
    def __init__(self, message: str = "يجب ذكر سبب واضح للإجراء اليدوي لا يقل عن 10 أحرف"):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)
