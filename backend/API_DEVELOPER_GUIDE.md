# دليل مطوري Backend — نظام فواتير كهرباء السكن الجامعي ⚡

تم بناء وإعادة هيكلة الـ Backend باستخدام **Python / Django + Django REST Framework (DRF)**. يهدف هذا الدليل لمساعدتك على فهم الهيكل المخصص للمشروع وتطوير مزايا جديدة بشكل منسق وآمن.

---

## 📁 هيكل الملفات الجديدة والخاصة

تم تجميع الخدمات المساعدة وحماية النظام في المجلد الرئيسي `backend/api/` كالتالي:
- `exceptions.py`: يحتوي على كلاسات الاستثناءات المخصصة (بديل `AppError` المألوف في Node.js).
- `exception_handler.py`: المعالج المركزي لجميع أنواع الأخطاء (بما فيها أخطاء قاعدة البيانات والـ JWT).
- `middleware.py`: يحتوي على `NotFoundMiddleware` لاعتراض الروابط الخاطئة.
- `permissions.py`: نظام التحقق من الصلاحيات وربطها بالأدوار (RBAC).
- `ownership.py`: التحقق من ملكية البيانات للمندوبين الميدانيين والمحاسبين.

---

## 🛠️ 1. نظام معالجة الأخطاء المركزي (Centralized Error Handling)

يستخدم المشروع معالج استثناءات مركزي موحد يُرجع الردود دائماً بالتنسيق التالي:
```json
{
  "success": false,
  "status": "fail", // أو "error" لأخطاء الخادم 5xx
  "message": "رسالة الخطأ باللغة العربية"
}
```

### الاستخدام المباشر في الـ Views:
لإرجاع خطأ مخصص للعميل، لا تستخدم `raise Exception` بل استخدم الفئات المخصصة من `api.exceptions`:

```python
from api.exceptions import ValidationError, NotFoundError, ConflictError

# مثال 1: خطأ في البيانات المرسلة
raise ValidationError("قيمة القراءة الجديدة يجب أن تكون أكبر من القديمة")

# مثال 2: مورد غير موجود
raise NotFoundError("هذه الغرفة غير مسجلة في النظام")
```

---

## 🔐 2. نظام الصلاحيات والأدوار (Permissions / RBAC)

لدينا ثلاثة أدوار أساسية محددة بـ `ROLE_CHOICES` في الموديل `User`:
1. `admin` (المشرف الرئيسي)
2. `delegate` (المندوب الميداني)
3. `accountant` (المحاسب المالي)

> **قرار تصميمي هام:** تم الاعتماد على حقل `role` فقط لإدارة الصلاحيات لتجنب الازدواجية، وحقل `permissions` (من نوع JSON) محجوز حالياً للتوسعات المستقبلية.

### كيفية حماية الـ Views:
يمكنك استخدام الصلاحيات الجاهزة مباشرة داخل الـ ViewSets:

```python
from rest_framework import viewsets
from api.permissions import IsAuthenticatedCustom, IsAdminUser, IsDelegate, IsAdminOrDelegate

class InvoiceViewSet(viewsets.ModelViewSet):
    # IsAuthenticatedCustom: تتأكد من تسجيل الدخول وتواجد JWT
    # IsAdminOrDelegate: تسمح فقط للمشرف والمندوب بإنشاء الفاتورة
    permission_classes = [IsAuthenticatedCustom, IsAdminOrDelegate]
```

### استخدام الـ Factory ديناميكياً:
إذا أردت دمج أدوار مخصصة مباشرة في أي مكان دون كتابة shortcut مسبقاً، يمكنك استخدام الـ Factory `RestrictTo`:

```python
from api.permissions import RestrictTo, ROLE_ADMIN, ROLE_ACCOUNTANT

permission_classes = [RestrictTo(ROLE_ADMIN, ROLE_ACCOUNTANT)]
```

---

## 🏠 3. نظام ملكية البيانات (Ownership Check)

لمنع المندوبين من الاطلاع على فواتير أو غرف غير تابعة لهم، يُطبق كلاس `CheckOwnership` على مستوى كائن البيانات الفعلي (Object-level Permission):

```python
from api.permissions import IsAuthenticatedCustom
from api.ownership import CheckOwnership

class InvoiceViewSet(viewsets.ModelViewSet):
    # يمنع المندوب من الوصول لفاتورة لم يقم بإنشائها بنفسه
    # بينما يسمح للمشرف (admin) بالوصول الكامل لجميع الفواتير
    permission_classes = [IsAuthenticatedCustom, CheckOwnership]
```

> **ملاحظة للمستقبل:** الكود الحالي لـ `CheckOwnership` يربط المندوب بالفواتير التي أنشأها بنفسه عبر `created_by`. يوجد `TODO` واضح في الملف لربط التحقق مستقبلاً بجدول تخصيص المباني للمندوبين جغرافياً.
