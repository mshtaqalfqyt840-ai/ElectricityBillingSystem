import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import User
u = User.objects.get(username='admin_main')
print('Old Password Hash:', u.password_hash)
u.password_hash = '12345678'
u.save()
print('Password successfully reset to: 12345678')
