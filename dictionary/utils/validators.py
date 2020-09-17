from django.core.validators import ValidationError, _lazy_re_compile  # noqa
from django.utils.html import mark_safe
from django.utils.translation import gettext as _

from uuslug import slugify

from dictionary.conf import settings


user_text_re = _lazy_re_compile(r"^[A-Za-z0-9 ğçıöşüĞÇİÖŞÜ#&@()_+=':%/\",.!?*~`\[\]{}<>^;\\|-]+$")
topic_title_re = _lazy_re_compile(r"^[a-z0-9 ğçıöşü&#()_+='%/\",.!?~\[\]{}<>^;\\|-]+$")


def validate_topic_title(value, exctype=ValidationError):
    if not slugify(value):
        raise exctype(_("that title is just too nasty."))

    if len(value) > 50:
        raise exctype(_("this title is too long"))

    if topic_title_re.fullmatch(value) is None:
        raise exctype(_("the definition of this topic includes forbidden characters"))


def validate_user_text(value, exctype=ValidationError):
    if len(value.strip()) < 1:
        raise exctype(_("my dear, just write your entry, how hard could it be?"))

    if user_text_re.fullmatch("".join(value.splitlines())) is None:
        args, kwargs = [_("this content includes forbidden characters.")], {}

        if exctype == ValidationError:
            kwargs["params"] = {"value": value}

        raise exctype(*args, **kwargs)


def validate_category_name(value):
    if slugify(value) in settings.NON_DB_CATEGORIES:
        message = _(
            "The channel couldn't be created as the name of this channel"
            " clashes with a reserved category lister. The complete list"
            " of forbidden names follows:"
        )
        raise ValidationError(mark_safe(f"<strong>{message}</strong><br>{'<br>'.join(settings.NON_DB_CATEGORIES)}"))


def validate_username_partial(value):
    if slugify(value) == "archive":
        raise ValidationError(_("this nickname is reserved by the boss"))
