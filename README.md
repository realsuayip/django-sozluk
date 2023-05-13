## django-sozluk, ekşi sözlük clone powered by Python
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)

Demo website is now available at [sozluk.me](https://sozluk.me/) \
Check [CHANGELOG](CHANGELOG) before cloning a newer version!

This is a clone of ekşi sözlük. Commonly referred as "collaborative dictionary",
this type of social networking can be thought as "urban dictionary on steroids". Visit
[this Wikipedia article](https://en.wikipedia.org/wiki/Ek%C5%9Fi_S%C3%B6zl%C3%BCk) to learn more about
this type of social network.


**This project is currently maintained.** If you want to contribute to the project or have found a bug
or need help about deployment etc., you may contact me via
Telegram (I use the same username there) or, better yet, [create an issue](https://github.com/realsuayip/django-sozluk/issues/new).

Check out "todo" keyword in the project files or Github issues to see the to-do's.

Check out [screenshots](screenshots) folder to see current front-end in action with both the desktop and mobile views.

### Quick installation

Installation requires Docker (with compose plugin) and GNU Makefile installed.
Run this command in the project root:

    make

This will build and start development server for the project. Keep in mind that
in development mode, the emails will output into console (container logs).

Running in development mode will also create a superuser with email `test@django.org` and password
`test`. In order for your entries to appear, you need to make yourself an actual author i.e.,
remove yourself from novice status using admin user edit page.

The website uses cache mechanism frequently, so you may be inclined to disable
caching using a dummy cache backend, or disabling cache on left frame. Check settings
on `apps.py` to learn about caching and about all the other settings.

A production setup is also available if you set `CONTEXT` environment variable
to `production`. For example, to do deployment in production mode you would run:

    CONTEXT=production make

If you are going to use the production setup, you'll need to run setup script
once, after the initial build completes (otherwise a server error is shown):

    CONTEXT=production make setup

Makefile also includes other miscellaneous commands. You can browse it to learn
more.

### Standard docker usage
If you prefer not use the helper script to gain more granular control, make sure you specify
the right compose file. Use this command to build and serve:

    docker-compose -f docker/docker-compose.yml up -d

Initially, you also have to run a script (in the web container) that sets up the
database, collects static files and generates required users for the dictionary app:

    docker-compose exec web sh docker/scripts/setup.sh

You are most likely to create an admin account after these processes:

    docker-compose exec web python manage.py createsuperuser

If you intend to use this configuration for production, make sure you have
edited all the `.env` files, Django settings file (`settings_prod.py`) and
dictionary settings file (`dictionary/apps.py`) with proper credentials.
Make sure you change the passwords of users that are generated
through `setup.sh` script.
