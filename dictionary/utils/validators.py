import re

from django.core.validators import ValidationError, _lazy_re_compile
from django.utils.html import mark_safe

from uuslug import slugify

from .settings import NON_DB_CATEGORIES


user_text_re = _lazy_re_compile(r"^[A-Za-z0-9 ğçıöşüĞÇİÖŞÜ#&@()_+=':%/\",.!?*~`\[\]{}<>^;\\|-]+$")


def validate_user_text(value):
    if re.fullmatch(user_text_re, "".join(value.splitlines())) is None:
        raise ValidationError("bu içerik geçersiz karakterler içeriyor", params={"value": value})


def validate_category_name(value):
    if slugify(value) in NON_DB_CATEGORIES:
        raise ValidationError(
            mark_safe(
                f"<strong>Bu kanalın ismi özel başlık listeyicilerden biriyle"
                f" tamamen örtüştüğü için bu ismi kullanamazsınız. "
                f" Yasaklı isimlerin tam listesi şöyle:"
                f"</strong><br>{f'<br>'.join(NON_DB_CATEGORIES)}"
            )
        )
