import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')

import django
django.setup()

from django.core.management import call_command

try:
    print("Starting Django development server...")
    call_command('runserver', '8000', '--noreload')
except KeyboardInterrupt:
    print("\nServer stopped.")
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
