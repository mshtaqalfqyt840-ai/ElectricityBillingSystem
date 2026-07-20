"""
api/ownership.py
مكافئ ownership.js — middleware للتحقق من ملكية البيانات للمندوبين والمحاسبين.
"""
from rest_framework import permissions
from .exceptions import PermissionDeniedError

# قرار تصميمي صريح:
# تم الاعتماد على role فقط، permissions JSON غير مستخدم حالياً لتجنب الازدواجية.
# حقل permissions في جدول users محجوز للتوسعات المستقبلية.

class CheckOwnership(permissions.BasePermission):
    """
    CheckOwnership:
    يتحقق مما إذا كان المستخدم يملك المورد المطلوب (مثلاً: الفواتير التي أنشأها المندوب).
    
    - المشرف (admin): يسمح له بكل شيء.
    - المندوب (delegate):
        - بالنسبة للفواتير: يسمح له فقط بالوصول للفواتير التي قام بإنشائها (invoice.created_by == request.user).
        - بالنسبة للغرف والمباني:
            # TODO: لاحقاً يجب ربط المندوب بجدول تخصيص المباني (DelegateBuilding / BuildingAssignment)
            # للتحقق من أن الغرفة/المبنى المطلوب يقع ضمن صلاحياته الجغرافية المخصصة له.
    - المحاسب (accountant):
        - يسمح له برؤية الفواتير المعتمدة أو جميعها، ولكن لا يعدل إلا المسموح له.
    """
    message = "ليس لديك صلاحية للوصول لهذا المورد (ليست من إنشائك أو خارج نطاق صلاحياتك)"

    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # إذا لم يكن مسجلاً الدخول أصلاً
        if not user or not user.is_authenticated:
            return False
            
        # 1. المشرف (admin) مسموح له بكل شيء
        if user.role == 'admin':
            return True
            
        # 2. المندوب (delegate)
        if user.role == 'delegate':
            model_name = obj.__class__.__name__.lower()
            
            if model_name == 'invoice':
                # يسمح له فقط بالوصول للفواتير التي أنشأها
                is_owner = obj.created_by == user
                if not is_owner:
                    raise PermissionDeniedError("ليس لديك صلاحية للوصول لهذه الفاتورة (ليست من إنشائك)")
                return True
                
            elif model_name in ['room', 'building']:
                # TODO: لاحقاً لازم نربطه بجدول تخصيص المباني للمندوبين لو موجود
                # للتحقق من أن الغرفة أو المبنى يتبع للمندوب الحالي.
                return True
                
            elif model_name == 'student':
                # TODO: التحقق من أن مبنى الطالب يقع ضمن المباني المخصصة للمندوب
                return True
                
        # 3. المحاسب (accountant)
        if user.role == 'accountant':
            # المحاسب يرى الفواتير لكن لا يسمح له بتعديلها إلا من خلال actions معينة
            return True

        return False
