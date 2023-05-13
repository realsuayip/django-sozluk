#!/bin/sh

if [ "$DATABASE" = "postgres" ]; then
  echo "Checking for postgres..."

  while ! nc -z "$SQL_HOST" "$SQL_PORT"; do
    sleep 0.1
  done

  echo "PostgreSQL is up."
fi

chown :1017 "$APP_DIR" "$APP_DIR"/media "$APP_DIR"/static
chmod 775 "$APP_DIR"
chmod 775 -R "$APP_DIR"/media "$APP_DIR"/static

exec gosu django "$@"
