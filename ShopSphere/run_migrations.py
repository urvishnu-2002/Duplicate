import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')

import django
django.setup()

from django.core.management import call_command

try:
    call_command('makemigrations', verbosity=2)
    print("\nMigrations created successfully!")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
