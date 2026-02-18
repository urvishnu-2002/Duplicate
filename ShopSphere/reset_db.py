import os
import shutil
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')
django.setup()

from django.core.management import call_command

def reset_database():
    print("⚠️  Starting Database Reset Process...")
    
    # 1. Delete db.sqlite3
    db_file = 'db.sqlite3'
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print(f"✅ Deleted old {db_file}")
        except PermissionError:
            print(f"❌ Error: Could not delete {db_file}. Please close any programs using the database (like DB Browser) and try again.")
            return

    # 2. Delete migration files (keep __init__.py)
    apps = ['user', 'vendor', 'deliveryAgent', 'superAdmin']
    base_dir = os.getcwd()
    
    print("🧹 Cleaning migration files...")
    for app in apps:
        migrations_path = os.path.join(base_dir, app, 'migrations')
        if os.path.exists(migrations_path):
            for filename in os.listdir(migrations_path):
                if filename != '__init__.py' and filename.endswith('.py'):
                    file_path = os.path.join(migrations_path, filename)
                    try:
                        os.remove(file_path)
                        print(f"   - Deleted {app}/migrations/{filename}")
                    except Exception as e:
                        print(f"   ! Failed to delete {filename}: {e}")
                elif filename == '__pycache__':
                    shutil.rmtree(os.path.join(migrations_path, filename))

    # 3. Create static folder if missing (fixes warning)
    static_dir = os.path.join(base_dir, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        print(f"✅ Created missing directory: {static_dir}")

    # 4. Run makemigrations
    print("\n🔄 Running makemigrations...")
    call_command('makemigrations')

    # 5. Run migrate
    print("\n🔄 Running migrate...")
    call_command('migrate')

    print("\n✅ SUCCESS: Database reset complete!")

if __name__ == '__main__':
    reset_database()