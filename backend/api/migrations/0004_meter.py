# Generated manually — Django 5.2.16
#
# يُنشئ جدول meters لتخزين بيانات العداد الذكي المرتبط بكل غرفة (One-to-One).
# القيمة الافتراضية لـ connection_status هي 'connected'
# لضمان أن أي عداد يُضاف يكون في حالة توصيل مبدئياً.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_invoice_overdue_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Meter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meter_serial', models.CharField(max_length=100)),
                ('connection_status', models.CharField(choices=[('connected', 'موصّل'), ('disconnected', 'مفصول')], default='connected', max_length=20)),
                ('last_command_sent_at', models.DateTimeField(blank=True, null=True)),
                ('last_command_status', models.CharField(blank=True, max_length=100, null=True)),
                ('room', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='meter', to='api.room')),
            ],
            options={
                'db_table': 'meters',
                'managed': True,
            },
        ),
    ]
