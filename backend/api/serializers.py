from rest_framework import serializers
from .models import Building, Room, Student, User, Invoice, SystemSettings, Complaint
from .exceptions import ValidationError as AppValidationError


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = '__all__'


class RoomSerializer(serializers.ModelSerializer):
    building_name = serializers.CharField(source='building.name', read_only=True)
    search_code = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ['id', 'room_number', 'building', 'building_name', 'qr_code', 'search_code']

    def get_search_code(self, obj):
        # Building code 1 (A) and 2 (B) get '0' + code suffix. Others (like C=3) stay normal.
        if obj.building.code in ['1', '2']:
            return f"{obj.room_number}0{obj.building.code}"
        return str(obj.room_number)


class StudentSerializer(serializers.ModelSerializer):
    room_qr = serializers.CharField(source='room.qr_code', read_only=True)
    room_search_code = serializers.CharField(source='room.search_code', read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'name', 'phone', 'room', 'room_qr', 'room_search_code', 'status', 'created_at']
        read_only_fields = ['created_at']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password_hash', 'role', 'permissions', 'created_at']
        read_only_fields = ['created_at']
        extra_kwargs = {
            'password_hash': {'write_only': True}
        }

    def create(self, validated_data):
        if 'password_hash' in validated_data:
            from django.contrib.auth.hashers import make_password
            validated_data['password_hash'] = make_password(validated_data['password_hash'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'password_hash' in validated_data:
            from django.contrib.auth.hashers import make_password
            validated_data['password_hash'] = make_password(validated_data['password_hash'])
        return super().update(instance, validated_data)


class InvoiceSerializer(serializers.ModelSerializer):
    room_qr = serializers.CharField(source='room.qr_code', read_only=True)
    room_search_code = serializers.CharField(source='room.search_code', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, default=None)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True, default=None)
    payment_deadline = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'room', 'room_qr', 'room_search_code', 'created_by', 'created_by_username',
            'approved_by', 'approved_by_username', 'reading_old', 'reading_new',
            'consumption', 'unit_price', 'total_amount', 'previous_debt',
            'final_amount', 'is_overdue', 'overdue_fine',
            'status', 'meter_image_url', 'created_at', 'payment_deadline',
        ]
        read_only_fields = ['created_at', 'is_overdue', 'overdue_fine', 'payment_deadline']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import SystemSettings
        self._settings_obj = SystemSettings.get_settings()

    def get_payment_deadline(self, obj):
        from datetime import timedelta
        deadline = obj.created_at + timedelta(hours=self._settings_obj.payment_deadline_hours)
        return deadline.isoformat()

    def validate(self, data):
        reading_old = data.get('reading_old')
        reading_new = data.get('reading_new')
        if reading_old is not None and reading_new is not None:
            if reading_new < reading_old:
                raise serializers.ValidationError(
                    "القراءة الجديدة لازم تكون أكبر من أو تساوي القراءة القديمة."
                )
        return data


class SystemSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer للإعدادات المالية العامة — Singleton.
    يتحقق من أن emergency_surcharge_min أصغر من emergency_surcharge_max دائماً.
    """

    class Meta:
        model  = SystemSettings
        fields = [
            'official_kwh_price',
            'emergency_surcharge_min',
            'emergency_surcharge_max',
            'service_fee',
            'reconnect_debt_threshold',
            'payment_deadline_hours',
            'anomaly_threshold_percentage',
        ]

    def validate(self, data):
        """
        مكافئ البند 5 من المتطلبات:
        يتأكد أن الحد الأدنى لرسوم الطوارئ أصغر من الحد الأقصى.
        يستخدم AppValidationError لضمان التقاطه بالمعالج المركزي.
        """
        # في حالة PATCH قد يُرسَل حقل واحد فقط، لذا نرجع للقيم المحفوظة
        instance = getattr(self, 'instance', None)
        min_val = data.get(
            'emergency_surcharge_min',
            getattr(instance, 'emergency_surcharge_min', None)
        )
        max_val = data.get(
            'emergency_surcharge_max',
            getattr(instance, 'emergency_surcharge_max', None)
        )

        if min_val is not None and max_val is not None:
            if min_val >= max_val:
                raise AppValidationError(
                    "الحد الأدنى لرسوم الطوارئ يجب أن يكون أصغر من الحد الأقصى تماماً."
                )
        return data


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ComplaintSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    room_qr = serializers.CharField(source='student.room.qr_code', read_only=True)
    room_search_code = serializers.CharField(source='student.room.search_code', read_only=True)

    class Meta:
        model = Complaint
        fields = ['id', 'student', 'student_name', 'room_qr', 'room_search_code', 'subject', 'message', 'status', 'created_at']
        read_only_fields = ['created_at', 'status']

    def create(self, validated_data):
        # Override create to ensure status is 'new' upon creation
        validated_data['status'] = 'new'
        return super().create(validated_data)


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True, default=None)

    class Meta:
        from .models import AuditLog
        model = AuditLog
        fields = ['id', 'actor', 'actor_username', 'action_type', 'target_model', 'target_id', 'description', 'metadata', 'created_at']
        read_only_fields = fields
