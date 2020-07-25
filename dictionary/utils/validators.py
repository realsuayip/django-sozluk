import re

from django.core.validators import ValidationError, _lazy_re_compile
from django.utils.html import mark_safe
from django.utils.translation import gettext as _

from uuslug import slugify

from .settings import NON_DB_CATEGORIES


user_text_re = _lazy_re_compile(r"^[A-Za-z0-9 ğçıöşüĞÇİÖŞÜ#&@()_+=':%/\",.!?*~`\[\]{}<>^;\\|-]+$")


def validate_user_text(value):
    if re.fullmatch(user_text_re, "".join(value.splitlines())) is None:
        raise ValidationError(_("this content includes forbidden characters."), params={"value": value})


def validate_category_name(value):
    if slugify(value) in NON_DB_CATEGORIES:
        message = _(
            "The channel couldn't be created as the name of this channel"
            " clashes with a reserved category lister. The complete list"
            " of forbidden names follows:"
        )
        raise ValidationError(mark_safe(f"<strong>{message}</strong><br>{'<br>'.join(NON_DB_CATEGORIES)}"))


def validate_username_partial(value):
    if slugify(value) == "archive":
        raise ValidationError(_("this nickname is reserved by the boss"))
