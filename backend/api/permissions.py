"""
api/permissions.py
مكافئ auth.js (protect + restrictTo) — نظام التحقق من الصلاحيات والأدوار

قرار تصميمي صريح:
    تم الاعتماد على role فقط، permissions JSON غير مستخدم حالياً لتجنب الازدواجية.
    حقل permissions في جدول users محجوز للتوسعات المستقبلية (مثل صلاحيات مبنى بعينه).
    كل صلاحية الآن تُحدَّد حصراً من قيمة role ENUM: admin | delegate | accountant.
"""
from rest_framework import permissions

from .exceptions import UnauthorizedError, PermissionDeniedError


# ── الأدوار المتاحة في النظام ──
ROLE_ADMIN = 'admin'
ROLE_DELEGATE = 'delegate'
ROLE_ACCOUNTANT = 'accountant'
ROLE_CASHIER = 'cashier'

ALL_ROLES = {ROLE_ADMIN, ROLE_DELEGATE, ROLE_ACCOUNTANT, ROLE_CASHIER}


class IsAuthenticatedCustom(permissions.BasePermission):
    """
    مكافئ protect في Express:
    يتحقق من وجود مستخدم مصادق عليه في req.user (يُحقنه CustomJWTAuthentication).
    يرفض بـ 401 مع رسالة عربية موحّدة.

    ملاحظة: التحقق الفعلي من التوكن وجلب المستخدم من DB يتم في:
        api/authentication.py → CustomJWTAuthentication.get_user()
    هذا الكلاس يتحقق فقط إن العملية نجحت.
    """
    message = 'يجب تسجيل الدخول أولاً للوصول لهذا المورد'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise UnauthorizedError(self.message)
        return True


def RestrictTo(*allowed_roles: str):
    """
    مكافئ restrictTo(...roles) في Express:
    دالة factory ترجع class يرث من BasePermission.
    
    الاستخدام:
        permission_classes = [IsAuthenticatedCustom, RestrictTo(ROLE_ADMIN, ROLE_DELEGATE)]
    """
    # التحقق من صحة الأدوار المدخلة عند التعريف
    roles_set = set(allowed_roles)
    invalid = roles_set - ALL_ROLES
    if invalid:
        raise ValueError(
            f"RestrictTo: أدوار غير صالحة {invalid}. الأدوار المتاحة: {ALL_ROLES}"
        )

    class RestrictToPermission(permissions.BasePermission):
        allowed_roles = roles_set

        def has_permission(self, request, view):
            user = request.user
            if not user or not user.is_authenticated:
                raise UnauthorizedError('يجب تسجيل الدخول أولاً')

            if user.role not in self.allowed_roles:
                roles_display = ' أو '.join(self._role_display(r) for r in self.allowed_roles)
                raise PermissionDeniedError(
                    f'هذه العملية مخصصة لـ {roles_display} فقط'
                )
            return True

        @staticmethod
        def _role_display(role: str) -> str:
            """تحويل role الإنجليزي لعرض عربي في رسائل الخطأ"""
            return {'admin': 'المشرف الرئيسي', 'delegate': 'المندوب الميداني', 'accountant': 'المحاسب المالي', 'cashier': 'أمين المكتب'}.get(role, role)

    # إعطاء اسم معبر للكلاس لمساعدة DRF في الـ documentation والـ logs
    roles_str = "".join(r.capitalize() for r in allowed_roles)
    RestrictToPermission.__name__ = f"RestrictTo{roles_str}Permission"
    
    return RestrictToPermission


# ── Shortcuts جاهزة للاستخدام المباشر ──

IsAdminUser = RestrictTo(ROLE_ADMIN)
IsDelegate = RestrictTo(ROLE_DELEGATE)
IsAccountant = RestrictTo(ROLE_ACCOUNTANT)
IsCashier = RestrictTo(ROLE_CASHIER)
IsAdminOrDelegate = RestrictTo(ROLE_ADMIN, ROLE_DELEGATE)
IsAdminOrAccountant = RestrictTo(ROLE_ADMIN, ROLE_ACCOUNTANT)
IsAdminOrAccountantOrCashier = RestrictTo(ROLE_ADMIN, ROLE_ACCOUNTANT, ROLE_CASHIER)


