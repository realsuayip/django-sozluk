files_env := env("SOZLUK_COMPOSE_FILES", "compose.yml workers.yml")
files_abs := prepend("docker/dev/", files_env)
files := prepend("-f ", files_abs)
service := "sozluk-web"

_default: (docker 'up -d')

# Run a docker-compose command
docker *args:
    docker compose -p sozluk {{ files }} {{ args }}

# Build Docker containers
build *args: (docker 'build' args)

# Start docker containers and attach to them
up *args: (docker 'up' args)

# Stop all Docker containers
stop *args: (docker 'stop' args)

# Run a shell command in Django container
exec *args:
    docker exec -it {{ service }} {{ args }}

# Enter Django container console
console *args: (exec '/bin/sh' args)

# Expose uv interface
uv *args: (exec 'uv' args)

# Create or update translation files
makemessages: (exec '/bin/sh -c "python manage.py makemessages --all --no-obsolete"')

# Compile translation files
compilemessages: (exec '/bin/sh -c "python manage.py compilemessages --ignore .venv"')

# Compile documentation
docs:
    make -C docs clean html

# Run pre-commit
format *args:
    pre-commit run {{ args }}

# Follow logs for given container.
logs container=service:
    docker logs {{ container }} --tail 500 --follow

# Execute a Django management command
run *args:
    docker exec -it {{ service }} python manage.py {{ args }}

# Enter Django shell
shell: (run 'shell')

alias f := format
alias l := logs
