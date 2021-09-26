#!/bin/sh

if [ "$DATABASE" = "postgres" ]; then
  echo "Checking for postgres..."

  while ! nc -z "$SQL_HOST" "$SQL_PORT"; do
    sleep 0.1
  done

  echo "PostgreSQL is up."
fi

export DJANGO_SUPERUSER_PASSWORD=test
python manage.py makemigrations
python manage.py migrate
python manage.py create_generic_user superuser BVT8WnWNF8wJvb4K superuser@example.com --no-input
python manage.py create_generic_user private BVT8WnWNF8wJvb4K private@example.com --no-input
python manage.py createsuperuser --username admin --email test@django.org --is_active 1 --no-input

exec "$@"
