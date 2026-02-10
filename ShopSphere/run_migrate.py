import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')

import django
django.setup()

from django.core.management import call_command

try:
    print("Running migrate...")
    call_command('migrate', verbosity=2)
    print("\nMigrations applied successfully!")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
