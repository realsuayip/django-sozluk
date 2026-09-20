import datetime
import hashlib
import typing
from functools import partial
from typing import Any
from urllib.parse import ParseResult
from uuid import uuid4

from django.core.mail import EmailMessage
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.encoding import force_str
from django.utils.translation import gettext

from dictionary.conf import settings
from djdict.celery import app


class Message(typing.NamedTuple):
    title: str
    content: str


@transaction.atomic
def send_email_confirmation(user, to_email):
    from dictionary.models import UserVerification  # noqa: PLC0415

    token = uuid4()
    token_hashed = hashlib.blake2b(token.bytes).hexdigest()
    expiration_date = timezone.now() + datetime.timedelta(days=1)
    verification = UserVerification.objects.create(
        author=user,
        verification_token=token_hashed,
        expiration_date=expiration_date,
        new_email=to_email,
    )

    p = ParseResult(
        scheme=settings.PROTOCOL,
        netloc=settings.DOMAIN,
        path=reverse(
            "confirm-email",
            kwargs={"token": str(token)},
        ),
        params="",
        query="",
        fragment="",
    )
    send_email = partial(
        send,
        "email_confirmation.html",
        title=gettext("e-mail confirmation"),
        recipients=[verification.new_email],
        context={
            "username": user.username,
            "confirm_url": p.geturl(),
        },
    )
    transaction.on_commit(send_email)


def _send_sync(
    template: str,
    *,
    title: str,
    content: str = "",
    recipients: list[str],
    context: dict[str, Any] | None = None,
    language: str,
) -> int:
    context = context or {}
    context.setdefault("title", title)
    context.setdefault("content", content)

    template = f"mailing/{template}"

    with translation.override(language):
        body = render_to_string(template, context=context)
        email = EmailMessage(
            force_str(title),
            body,
            to=recipients,
            from_email=settings.FROM_EMAIL,
        )

    email.content_subtype = "html"
    return email.send()


@app.task(name="send_email")
def _send_async(*args: Any, **kwargs: Any) -> int:
    return _send_sync(*args, **kwargs)


def send(
    template: str,
    *,
    title: str,
    content: str = "",
    recipients: list[str],
    context: dict[str, Any] | None = None,
    language: str | None = None,
    sync: bool = False,
) -> int:
    language = language or translation.get_language()
    with translation.override(language):
        args: Any = [template]
        kwargs: Any = {
            "title": force_str(title),
            "content": force_str(content),
            "recipients": recipients,
            "context": context,
            "language": language,
        }
    if sync:
        return _send_sync(*args, **kwargs)
    _send_async.apply_async(args=args, kwargs=kwargs)
    return 0
