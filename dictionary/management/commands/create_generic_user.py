from django.core.validators import validate_email
from django.db.utils import IntegrityError

from ...models import Author
from ...utils.settings import GENERIC_PRIVATEUSER_USERNAME, GENERIC_SUPERUSER_USERNAME
from . import BaseDebugCommand


# Creates generic users.


class Command(BaseDebugCommand):
    help = "Generic kullanıcı oluşturur."

    def add_arguments(self, parser):
        parser.add_argument("user-type", type=str, help="Oluşturulacak kullanıcın tipi")
        parser.add_argument("password", type=str, help="Oluşturulacak kullanıcın parolası")
        parser.add_argument("email", type=str, help="Oluşturulacak kullanıcın e-posta adresi")

    def handle(self, **options):
        available_types = ("private", "superuser")
        user_type = options.get("user-type")
        email = options.get("email")

        validate_email(email)  # Throws django.core.exceptions.ValidationError if not valid.

        if user_type not in available_types:
            raise ValueError(f"Kullanıcı tipi geçersiz, geçerli seçenekler: {available_types}.")

        is_private = user_type == "private"
        username = GENERIC_PRIVATEUSER_USERNAME if is_private else GENERIC_SUPERUSER_USERNAME

        confirmation = input(
            f"{username} ismiyle {user_type} tipiyle ve {email}"
            f" e-posta adresiyle oluşturulacak. devam edilsin mi? y/N: "
        )

        if confirmation == "y":
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
                    f"{guser.username} ismi ve {guser.email} e-posta adresiyle"
                    f" generic_{user_type} oluşturuldu. daha sonra arzu ederseniz"
                    f" bu kullanıcıyı admin sitesinde bulabilirsiniz."
                )
            except IntegrityError:
                self.stdout.write("Hata: Bu isimle bir kullanıcı zaten oluşturulmuş veya e-posta adresi kullanımda.")
        else:
            self.stdout.write("İşlem iptal edildi.")
