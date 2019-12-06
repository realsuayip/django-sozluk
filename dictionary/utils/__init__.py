# General utilities


def turkish_lower(turkish_string):
    lower_map = {ord(u'I'): u'ı', ord(u'İ'): u'i', }
    return turkish_string.translate(lower_map).lower()
