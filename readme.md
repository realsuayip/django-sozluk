## django-sozluk, ekşi sözlük clone powered by Python

This project is subject to further development, check out "todo"    keyword in the project files to see the to-do's.

Check out screenshots folder to see current front-end in action with both the desktop and mobile views.
   
No extra actions needed other than migrations and creation of admin account (make sure to remove the account from "çaylak listesi" so as to have the entries published). Check out djangoproject.com to see how to handle deployment procedures if you already don't know. Make sure to have your local email server set up with this command, if needed (if the port 1025 is already in use, change it also in the settings):

    python -m smtpd -n -c DebuggingServer localhost:1025

Python 3.6+ and Django 2+ required (in my development environment, the versions are 3.7.2 and 2.2.3 respectively). Other dependencies are stated in requirements file.

 If you want to contribute to the project or have found a bug or need help about deployment etc., please contact me.

