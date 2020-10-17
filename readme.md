## django-sozluk, ekşi sözlük clone powered by Python
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/6c2a34dfbd184f139cd32f8f622d4002)](https://www.codacy.com/manual/realsuayip/django-sozluk?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=realsuayip/django-sozluk&amp;utm_campaign=Badge_Grade)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)

Check [CHANGELOG](CHANGELOG) before cloning a newer version!

This is a clone of ekşi sözlük. Commonly referred as "collaborative dictionary",
this type of social networking can be thought as "urban dictionary on steroids". Visit
[this Wikipedia article](https://en.wikipedia.org/wiki/Ek%C5%9Fi_S%C3%B6zl%C3%BCk) to learn more about
this type of social network.

[Installation guide](docs/turkish/installation.md) is now available in Turkish!

If you want to contribute to the project or have found a bug
or need help about deployment etc., you may contact me via
Telegram (I use the same username there) or [create an issue](https://github.com/realsuayip/django-sozluk/issues/new).

Check out "todo" keyword in the project files or Github issues to see the to-do's.

Check out [screenshots](screenshots) folder to see current front-end in action with both the desktop and mobile views.
   
To run the site in development mode, follow regular procedures (setting up virtual environment, installing requirements etc.),
then create generic users using `create_generic_user` command provided by dictionary app. More information can be found
about this command via `--help`. Check out djangoproject.com to see how to handle deployment procedures if you already don't know. 

To receive e-mails in development, make sure that a Celery worker is running in background. The default set-up allows output in console; have your local email server set up with this command, (if the port 1025 is already in use, change it also in the settings):

    python -m smtpd -n -c DebuggingServer localhost:1025

Python 3.8.2+ required.
