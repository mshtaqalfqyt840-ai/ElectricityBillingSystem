import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Building

def list_buildings():
    print(list(Building.objects.values('id', 'name', 'code')))

if __name__ == '__main__':
    list_buildings()
