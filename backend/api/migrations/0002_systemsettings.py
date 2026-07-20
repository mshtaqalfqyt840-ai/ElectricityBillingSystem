# Generated manually — Django 5.2.16
#
# يُنشئ جدول system_settings ثم يُدرج الصف الوحيد (pk=1) بالقيم الافتراضية
# عبر RunPython، حتى يكون نظام الإعدادات جاهزاً فور تشغيل migrate.

from django.db import migrations, models


def create_initial_settings(apps, schema_editor):
    """تهيئة الإعدادات الافتراضية عند أول تشغيل للـ Migration"""
    SystemSettings = apps.get_model('api', 'SystemSettings')
    if not SystemSettings.objects.exists():
        SystemSettings.objects.create(
            pk=1,
            official_kwh_price=0.0,
            emergency_surcharge_min=5.0,
            emergency_surcharge_max=10.5,
            service_fee=150.0,
            reconnect_debt_threshold=300.0,
            payment_deadline_hours=48,
        )


def reverse_initial_settings(apps, schema_editor):
    """عكس عملية الإنشاء عند التراجع عن الـ Migration"""
    SystemSettings = apps.get_model('api', 'SystemSettings')
    SystemSettings.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('official_kwh_price', models.DecimalField(decimal_places=4, max_digits=10)),
                ('emergency_surcharge_min', models.DecimalField(decimal_places=2, default=5.0, max_digits=10)),
                ('emergency_surcharge_max', models.DecimalField(decimal_places=2, default=10.5, max_digits=10)),
                ('service_fee', models.DecimalField(decimal_places=2, default=150.0, max_digits=10)),
                ('reconnect_debt_threshold', models.DecimalField(decimal_places=2, default=300.0, max_digits=10)),
                ('payment_deadline_hours', models.IntegerField(default=48)),
            ],
            options={
                'db_table': 'system_settings',
                'managed': True,
            },
        ),
        migrations.RunPython(
            create_initial_settings,
            reverse_code=reverse_initial_settings,
        ),
    ]
