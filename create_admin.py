import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

def ensure_admin():
    User = get_user_model()
    username = os.environ.get('ADMIN_USERNAME', 'admin')
    password = os.environ.get('ADMIN_PASSWORD', '123')
    email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

    user, created = User.objects.get_or_create(username=username, defaults={'email': email})
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    action = 'Created' if created else 'Updated'
    print(f"{action} superuser '{username}' successfully.")

if __name__ == '__main__':
    ensure_admin()
