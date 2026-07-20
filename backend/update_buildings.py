import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Building

def update_building_codes():
    mapping = {
        'A': '1',
        'B': '2',
        'C': '3'
    }
    
    for name, code in mapping.items():
        # Find building by name first (since name was likely 'A', 'B', 'C')
        # We look for buildings whose name contains the letter to be safe
        buildings = Building.objects.filter(name__icontains=name)
        for b in buildings:
            print(f"Updating Building '{b.name}' (current code: {b.code}) to new code: '{code}'")
            b.code = code
            b.save()
            print(f"Success: {b}")

if __name__ == '__main__':
    update_building_codes()
