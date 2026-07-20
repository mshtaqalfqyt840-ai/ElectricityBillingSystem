import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Building

def fix_buildings():
    # Fix Test Building -> Building A (1)
    b_test = Building.objects.filter(id=19).first()
    if b_test:
        b_test.name = 'Building A'
        b_test.code = '1'
        b_test.save()
        print(f"Updated {b_test.name} to code {b_test.code}")

    # Fix Building B (2)
    b_b = Building.objects.filter(id=20).first()
    if b_b:
        b_b.code = '2'
        b_b.save()
        print(f"Updated {b_b.name} to code {b_b.code}")

    # Fix Building C (3)
    b_c = Building.objects.filter(id=21).first()
    if b_c:
        b_c.code = '3'
        b_c.save()
        print(f"Updated {b_c.name} to code {b_c.code}")

if __name__ == '__main__':
    fix_buildings()
