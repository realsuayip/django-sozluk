#!/bin/sh

if [ "$DATABASE" = "postgres" ]; then
  echo "Checking for postgres..."

  while ! nc -z "$SQL_HOST" "$SQL_PORT"; do
    sleep 0.1
  done

  echo "PostgreSQL is up."
fi

chown -R :1017 "$APP_DIR"
chmod 775 "$APP_DIR" "$APP_DIR"/media "$APP_DIR"/static

if [ "$DJ_INIT_SETUP" = "yes" ] && [ "$DJ_INIT_ENV" = "yes" ]; then
  echo "Starting initial setup..."
  python manage.py makemigrations
  python manage.py migrate
  python manage.py collectstatic --no-input
  python manage.py create_generic_user superuser BVT8WnWNF8wJvb4K superuser@example.com --no-input
  python manage.py create_generic_user private BVT8WnWNF8wJvb4K private@example.com --no-input
  echo "Done."
  echo "Please change the credentials of generic users using the admin page."
fi

exec gosu django "$@"
