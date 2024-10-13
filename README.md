## django-sozluk, ekşi sözlük clone powered by Python

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)

Demo website is now available at [sozluk.me](https://sozluk.me/) \
Check [CHANGELOG](CHANGELOG) before cloning a newer version!

This is a clone of ekşi sözlük. Commonly referred as "collaborative
dictionary", this type of social networking can be thought as "urban dictionary
on steroids". Visit
[this Wikipedia article](https://en.wikipedia.org/wiki/Ek%C5%9Fi_S%C3%B6zl%C3%BCk)
to learn more about this type of social network.

**This project is currently maintained.** If you want to contribute to the
project or have found a bug or need help about deployment
etc., [create an issue](https://github.com/realsuayip/django-sozluk/issues/new).

Check out [screenshots](screenshots) folder to see current front-end in action
with both the desktop and mobile views.

### Deployment Guide

#### Requirements

1. Have Docker, with Compose plugin (v2) installed in your system.
2. Have GNU make installed in your system.
3. Have your SSL certificates and dhparam file under `docker/prod/nginx/certs`.
   They should be named exactly as following: `server.crt`, `server.key`
   and `dhparam.pem`
4. Change and configure secrets in `django.env` and `postgres.env` files
   under `conf/prod`
5. Configure your preferences in `dictionary/apps.py`

#### Deployment

> [!IMPORTANT]
> When running any `make` command make sure `CONTEXT` environment variable is
> set to `production`

**In the project directory, run this command:**

```shell
CONTEXT=production make
```

At this point, your server will start serving requests via https port (443).
You should see a 'server error' page when you navigate to your website.

**To complete the installation, you need to run a initialization script:**

```shell
CONTEXT=production make setup
```

After running this command, you should be able to navigate through your website
without any issues. At this point, you should create an administrator account
to log in and manage your website:

```shell
CONTEXT=production make run createsuperuser
```
