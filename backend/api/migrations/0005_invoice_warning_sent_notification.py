# Generated manually — Django 5.2.16
#
# يُضيف حقل warning_sent على جدول invoices لمنع تكرار الإشعار الحرج،
# وينشئ جدول notifications لحفظ سجلات الإشعارات المُرسَلة.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_meter'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='warning_sent',
            field=models.BooleanField(default=False, help_text='True بعد إرسال الإنذار الحرج (5 ساعات أو أقل قبل انتهاء المهلة)'),
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('critical_warning', 'إنذار حرج - مهلة السداد')], default='critical_warning', max_length=50)),
                ('message', models.TextField()),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='api.invoice')),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='api.room')),
            ],
            options={
                'db_table': 'notifications',
                'managed': True,
            },
        ),
    ]
