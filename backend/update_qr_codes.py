import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Room

rooms = Room.objects.all()
updated = 0
for room in rooms:
    room.qr_code = str(uuid.uuid4())
    room.save()
    updated += 1

print(f"Successfully updated {updated} rooms with secure random QR codes.")
