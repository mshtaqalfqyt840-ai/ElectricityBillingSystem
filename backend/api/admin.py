from django.contrib import admin
from .models import Building, Room, Student, User, Invoice, SystemSettings

@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code')
    search_fields = ('name', 'code')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'room_number', 'building', 'qr_code')
    list_filter = ('building',)
    search_fields = ('qr_code',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'room', 'status', 'created_at')
    list_filter = ('status', 'room__building')
    search_fields = ('name', 'phone')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('username',)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'room', 'consumption', 'final_amount',
        'status', 'created_by', 'approved_by', 'created_at',
    )
    list_filter = ('status', 'room__building')
    search_fields = ('room__qr_code',)
    readonly_fields = ('created_at',)


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """
    لوحة تحكم الإعدادات المالية العامة — Singleton.
    • لا يُسمح بالحذف أبداً.
    • لا يُسمح بالإضافة إذا كان السجل موجوداً مسبقاً.
    """
    list_display = (
        'official_kwh_price',
        'emergency_surcharge_min',
        'emergency_surcharge_max',
        'service_fee',
        'reconnect_debt_threshold',
        'payment_deadline_hours',
    )

    def has_delete_permission(self, request, obj=None):
        """منع الحذف نهائياً — Singleton لا يُحذف"""
        return False

    def has_add_permission(self, request):
        """السماح بالإضافة فقط إذا لم يكن هناك أي سجل مسبقاً"""
        return not SystemSettings.objects.exists()
