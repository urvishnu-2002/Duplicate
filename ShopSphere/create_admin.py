
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ShopSphere.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = "admin"
email = "admin@example.com"
password = "Admin@123"

user = User.objects.filter(email=email).first()
if not user:
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"✅ Superuser created successfully!")
else:
    user.is_superuser = True
    user.is_staff = True
    user.set_password(password)
    user.save()
    print(f"✅ Superuser '{email}' updated successfully!")

print(f"--- Credentials ---")
print(f"Email: {email}")
print(f"Username: {username}")
print(f"Password: {password}")
print(f"-------------------")
print(f"You can now login at /superadmin/login/ using either the email or username.")
