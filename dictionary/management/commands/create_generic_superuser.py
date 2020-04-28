from django.db.utils import IntegrityError

from ...models import Author
from ...utils.email import FROM_EMAIL
from ...utils.settings import GENERIC_SUPERUSER_USERNAME
from . import BaseDebugCommand


# Creates generic superuser.


class Command(BaseDebugCommand):
    help = "generic_superuser oluşturur. e-posta belirtmezseniz FROM_EMAIL kullanılacak."

    def add_arguments(self, parser):
        parser.add_argument("password", nargs="?", type=str, help="oluşturulacak kullanıcın parolası")
        parser.add_argument(
            "--email", nargs="?", type=str, help="oluşturulacak kullanıcın e-posta adresi", default=FROM_EMAIL
        )

    def handle(self, **options):
        email = options.get("email")

        if email is None:
            raise ValueError("düzgün bir email adresi girin")

        confirmation = input(
            f"{GENERIC_SUPERUSER_USERNAME} ismiyle ve {email} e-posta adresiyle oluşturulacak. devam edilsin mi? y/N"
        )

        if confirmation == "y":
            try:
                gsuser = Author.objects.create_user(
                    username=GENERIC_SUPERUSER_USERNAME,
                    email=email,
                    is_active=True,
                    is_novice=False,
                    application_status="AP",
                    message_preference="DS",
                    password=options.get("password"),
                )

                self.stdout.write(
                    f"{gsuser.username} ismi ve {gsuser.email} e-posta adresiyle"
                    f" generic_superuser oluşturldu. daha sonra arzu ederseniz"
                    f" bu kullanıcıyı admin sitesinde bulabilirsiniz."
                )
            except IntegrityError:
                self.stdout.write("Hata: Bu isimle bir kullanıcı zaten oluşturulmuş veya e-posta adresi kullanımda.")

        self.stdout.write("vaz geçtiniz.")
