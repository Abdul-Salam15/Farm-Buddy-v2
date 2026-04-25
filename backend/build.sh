#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Create admin superuser if it doesn't already exist
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'asalamadebayo@gmail.com', 'admin')
    print('Superuser created: admin')
else:
    print('Superuser already exists: admin')
"
