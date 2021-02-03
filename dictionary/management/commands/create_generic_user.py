from django.core.management.base import BaseCommand
from django.core.validators import validate_email
from django.db.utils import IntegrityError
from django.utils.translation import gettext as _

from dictionary.conf import settings
from dictionary.models import Author

# Creates generic users.


class Command(BaseCommand):
    @property
    def help(self):
        return _("Creates a generic user")

    def add_arguments(self, parser):
        parser.add_argument("user-type", type=str, help=_("The type of the user to be created"))
        parser.add_argument("password", type=str, help=_("The password of the user to be created"))
        parser.add_argument("email", type=str, help=_("E-mail address of the user to bo be created"))
        parser.add_argument("--no-input", action="store_true")

    def handle(self, **options):
        available_types = ("private", "superuser")
        user_type = options.get("user-type")
        email = options.get("email")
        no_input = options.get("no_input")

        validate_email(email)  # Throws django.core.exceptions.ValidationError if not valid.

        if user_type not in available_types:
            raise ValueError(f"({_('Invalid user type, available types:')} {available_types}.")

        is_private = user_type == "private"
        username = settings.GENERIC_PRIVATEUSER_USERNAME if is_private else settings.GENERIC_SUPERUSER_USERNAME

        confirmation = (
            "y"
            if no_input
            else input(
                _(
                    "A user with username %(username)s, generic type %(user_type)s"
                    " and email %(email)s will be created. Continue? y/N: "
                )
                % {"username": username, "user_type": user_type, "email": email}
            )
        )

        if confirmation != "y":
            self.stdout.write(_("Command aborted."))
            return

        try:
            guser = Author.objects.create_user(
                username=username,
                email=email,
                is_active=True,
                is_novice=False,
                is_private=is_private,
                application_status="AP",
                message_preference="DS",
                password=options.get("password"),
            )

            self.stdout.write(
                _(
                    "generic_%(user_type)s has been created with the username"
                    " %(username)s and email %(email)s. You can edit the details"
                    " of this user via admin page if you wish."
                )
                % {"username": guser.username, "user_type": user_type, "email": guser.email}
            )
        except IntegrityError:
            self.stdout.write(_("Error: either there is an existing user with given username or e-mail is in use."))
