import datetime

from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from ..models import UserVerification


DOMAIN = "127.0.0.1:8000"
PROTOCOL = "http"
FROM_EMAIL = "test@django.org"


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return str(user.pk) + str(timestamp) + str(user.is_active)


def send_email_confirmation(user, to_email):
    token_generator = EmailVerificationTokenGenerator()
    verification_token_raw = token_generator.make_token(user)
    verification_token_hashed = make_password(verification_token_raw)
    expiration_date = timezone.now() + datetime.timedelta(days=1)
    UserVerification.objects.create(author=user, verification_token=verification_token_hashed,
                                    expiration_date=expiration_date, new_email=to_email)

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    params = {"domain": DOMAIN, "protocol": PROTOCOL, "user": user, "uidb64": uidb64, "token": verification_token_raw}
    msg = render_to_string("dictionary/registration/email/confirmation_email_template.html", params)
    return send_mail("email onayı", "email onayı", from_email=FROM_EMAIL, recipient_list=[to_email], html_message=msg,
                     fail_silently=True)
