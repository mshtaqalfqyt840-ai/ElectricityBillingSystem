# Generated manually — Django 5.2.16
#
# يُضيف حقلَي is_overdue وoverdue_fine إلى جدول invoices.
# القيم الافتراضية (False, 0) تعني أن جميع الفواتير الموجودة
# ستُعامَل كـ "غير متأخرة" حتى يُعاد التحقق منها عند طلبها.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_systemsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='is_overdue',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='invoice',
            name='overdue_fine',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
