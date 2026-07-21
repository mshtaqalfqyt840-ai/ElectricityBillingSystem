from django.db import models
import uuid


class Building(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(unique=True, max_length=1)

    class Meta:
        managed = True
        db_table = 'buildings'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Room(models.Model):
    room_number = models.IntegerField()
    building = models.ForeignKey(
        Building, on_delete=models.CASCADE, related_name='rooms'
    )
    qr_code = models.CharField(unique=True, max_length=50, default=uuid.uuid4)

    class Meta:
        managed = True
        db_table = 'rooms'
        unique_together = (('room_number', 'building'),)

    def __str__(self):
        return self.qr_code


class Student(models.Model):
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('left', 'غادر'),
    ]

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='students'
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'students'

    def __str__(self):
        return self.name


class User(models.Model):
    ROLE_CHOICES = [
        ('admin', 'مشرف'),
        ('delegate', 'مندوب'),
        ('accountant', 'محاسب'),
        ('cashier', 'أمين المكتب'),
    ]

    username = models.CharField(unique=True, max_length=100)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    permissions = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'users'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('approved', 'معتمدة'),
        ('paid', 'مدفوعة'),
    ]

    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='invoices'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices_created', db_column='created_by'
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices_approved', db_column='approved_by'
    )
    reading_old = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    reading_new = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    consumption = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    previous_debt = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_overdue   = models.BooleanField(default=False)
    overdue_fine = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    meter_image_url = models.CharField(max_length=255, blank=True, null=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    paid_at         = models.DateTimeField(blank=True, null=True, help_text="تاريخ الدفع الفعلي")
    warning_sent    = models.BooleanField(
        default=False,
        help_text="True بعد إرسال الإنذار الحرج (5 ساعات أو أقل قبل انتهاء المهلة)"
    )

    class Meta:
        managed = True
        db_table = 'invoices'

    def __str__(self):
        return f"فاتورة #{self.id} - {self.room}"


class SystemSettings(models.Model):
    """
    الإعدادات المالية العامة للنظام — Singleton (صف واحد لا يتكرر ولا يُحذف).
    استخدم get_settings() دائماً بدلاً من objects.get() أو objects.first() مباشرةً.
    """
    official_kwh_price       = models.DecimalField(max_digits=10, decimal_places=4)
    emergency_surcharge_min  = models.DecimalField(max_digits=10, decimal_places=2, default=5.0)
    emergency_surcharge_max  = models.DecimalField(max_digits=10, decimal_places=2, default=10.5)
    service_fee              = models.DecimalField(max_digits=10, decimal_places=2, default=150.0)
    reconnect_debt_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=300.0)
    payment_deadline_hours   = models.IntegerField(default=48)
    anomaly_threshold_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=50.0)

    class Meta:
        managed  = True
        db_table = 'system_settings'

    def save(self, *args, **kwargs):
        """يضمن الكتابة دائماً على نفس الصف (pk=1)"""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """لا يُحذف أبداً — يُتجاهل الأمر بصمت"""
        pass

    @classmethod
    def get_settings(cls):
        """استرجاع الإعدادات الوحيدة أو إنشاؤها بالقيم الافتراضية عند أول استدعاء"""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "الإعدادات المالية العامة للنظام"


class Meter(models.Model):
    """
    العداد الذكي المرتبط بغرفة سكنية — One-to-One مع Room.

    تصميمي: تم اختيار موديل منفصل بدلاً من إضافة الحقول لـ Room
    للفصل بين المسؤوليات:
      - Room   → كيان إداري (مبنى، رقم، QR)
      - Meter  → كيان تقني (حالة التوصيل، آخر أمر أُرسل للعداد)

    يُتيح هذا الفصل إضافة منطق العداد أو استبداله لاحقاً
    دون المساس بجدول rooms.
    """

    CONNECTION_CHOICES = [
        ('connected',    'موصّل'),
        ('disconnected', 'مفصول'),
    ]

    room = models.OneToOneField(
        Room, on_delete=models.CASCADE, related_name='meter'
    )
    meter_serial        = models.CharField(max_length=100)
    connection_status   = models.CharField(
        max_length=20, choices=CONNECTION_CHOICES, default='connected'
    )
    last_command_sent_at  = models.DateTimeField(blank=True, null=True)
    last_command_status   = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed  = True
        db_table = 'meters'

    def __str__(self):
        return f"عداد {self.meter_serial} — الغرفة {self.room}"


class Notification(models.Model):
    """
    سجل الإشعارات المُرسَلة للغرف.
    يُنشأ سجل جديد عند كل إشعار — لا يُحذف ولا يُعدَّل (append-only).

    notification_type القيم المدعومة حالياً:
      'critical_warning' — إنذار حرج قبل انتهاء مهلة السداد بـ 5 ساعات
    """

    TYPE_CHOICES = [
        ('critical_warning', 'إنذار حرج - مهلة السداد'),
        ('auto_disconnect', 'فصل آلي - انتهاء المهلة'),
    ]

    SMS_STATUS_CHOICES = [
        ('sent', 'تم الإرسال'),
        ('failed', 'فشل الإرسال'),
        ('not_configured', 'غير مهيأ'),
    ]

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='notifications'
    )
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=50, choices=TYPE_CHOICES, default='critical_warning'
    )
    message  = models.TextField()
    sent_at  = models.DateTimeField(auto_now_add=True)
    sms_status = models.CharField(
        max_length=20, choices=SMS_STATUS_CHOICES, default='not_configured'
    )

    class Meta:
        managed  = True
        db_table = 'notifications'

    def __str__(self):
        return f"إشعار [{self.notification_type}] — الغرفة {self.room} — {self.sent_at:%Y-%m-%d %H:%M}"


class Transaction(models.Model):
    STATUS_CHOICES = [
        ('pending', 'قيد التحقق'),
        ('verified', 'تم التحقق'),
        ('rejected', 'مرفوض'),
    ]

    transaction_id = models.CharField(unique=True, max_length=255)
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='transactions'
    )
    wallet_provider = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    verification_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'transactions'

    def __str__(self):
        return f"{self.transaction_id} - {self.get_verification_status_display()}"


class Complaint(models.Model):
    STATUS_CHOICES = [
        ('new', 'جديدة'),
        ('processing', 'قيد المعالجة'),
        ('closed', 'مغلقة'),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='complaints'
    )
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'complaints'

    def __str__(self):
        return f"شكوى #{self.id} - {self.student.name} ({self.get_status_display()})"


class InstallmentPlan(models.Model):
    STATUS_CHOICES = [
        ('active', 'نشطة'),
        ('completed', 'مكتملة'),
        ('defaulted', 'متعثرة'),
        ('cancelled', 'ملغاة'),
    ]
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='installment_plans')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    number_of_installments = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_installment_plans')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'installment_plans'

    def __str__(self):
        return f"خطة تقسيط للغرفة {self.room} ({self.get_status_display()})"


class InstallmentPayment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('paid', 'مدفوع'),
        ('overdue', 'متأخر'),
    ]
    plan = models.ForeignKey(InstallmentPlan, on_delete=models.CASCADE, related_name='payments')
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'installment_payments'
        ordering = ['due_date']

    def __str__(self):
        return f"قسط {self.amount} مستحق في {self.due_date}"


class ManualMeterAction(models.Model):
    ACTION_CHOICES = [
        ('connect', 'توصيل'),
        ('disconnect', 'فصل'),
    ]
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='manual_meter_actions')
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reason = models.TextField()
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'manual_meter_actions'

    def __str__(self):
        return f"{self.get_action_type_display()} لـ {self.room} بواسطة {self.performed_by}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('manual_meter_action', 'إجراء يدوي للعداد'),
        ('installment_plan_created', 'إنشاء خطة تقسيط'),
        ('settle_payment', 'تسوية سداد'),
        ('system_settings_updated', 'تحديث إعدادات النظام'),
        ('auto_disconnect', 'فصل آلي للعداد'),
        ('critical_warning_sent', 'إرسال إنذار حرج'),
        ('anomaly_override', 'تجاوز تحذير الاستهلاك الشاذ'),
        ('financial_report_generated', 'إنشاء تقرير مالي'),
    ]

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100)
    description = models.TextField()
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_type_display()} - {self.target_model} ({self.target_id})"

class ArchiveReport(models.Model):
    PERIOD_CHOICES = [
        ('half_month', 'نصف شهري'),
        ('month', 'شهري'),
        ('year', 'سنوي'),
    ]
    report_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    report_date = models.DateField(auto_now_add=True)
    
    total_kwh_consumption = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    total_amount_due = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    total_service_fees = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    total_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    remaining_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    net_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    
    expense_station_admin = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    expense_maintenance = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    expense_electricity_committee = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    expense_student_committee = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    expense_other_debts = models.DecimalField(max_digits=15, decimal_places=2, default=0.0)
    
    archived_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='archived_reports')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'archive_reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"تقرير {self.get_period_type_display()} - {self.report_date}"
