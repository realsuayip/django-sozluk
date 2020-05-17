import re

from django.core.validators import ValidationError, _lazy_re_compile


user_text_re = _lazy_re_compile(r"^[A-Za-z0-9 ğçıöşüĞÇİÖŞÜ#&@()_+=':%/\",.!?*~`\[\]{}<>^;\\|-]+$")


def validate_user_text(value):
    if re.fullmatch(user_text_re, "".join(value.splitlines())) is None:
        raise ValidationError("bu içerik geçersiz karakterler içeriyor", params={"value": value})
