import os
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')

try:
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'makemigrations'])
except Exception as e:
    with open('error_details.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("FULL ERROR:\n")
        f.write("=" * 80 + "\n")
        traceback.print_exc(file=f)
        f.write("=" * 80 + "\n")
    print("Error written to error_details.txt")
    sys.exit(1)
