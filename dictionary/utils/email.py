import datetime
import hashlib

from uuid import uuid4

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from ..models import UserVerification
from .settings import DOMAIN, FROM_EMAIL, PROTOCOL


def send_email_confirmation(user, to_email):
    token = uuid4()
    token_hashed = hashlib.blake2b(token.bytes).hexdigest()
    expiration_date = timezone.now() + datetime.timedelta(days=1)
    UserVerification.objects.create(
        author=user, verification_token=token_hashed, expiration_date=expiration_date, new_email=to_email
    )

    params = {"domain": DOMAIN, "protocol": PROTOCOL, "user": user, "token": str(token)}
    body = render_to_string("dictionary/registration/email/confirmation_email_template.html", params)

    email = EmailMessage(_("e-mail confirmation"), body, FROM_EMAIL, [to_email])
    email.content_subtype = "html"
    return email.send()
