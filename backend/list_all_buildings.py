import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Building

def list_buildings():
    buildings = Building.objects.all().values('id', 'name', 'code')
    print("Current Buildings:")
    for b in buildings:
        print(b)

if __name__ == '__main__':
    list_buildings()
