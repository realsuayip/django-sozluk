import datetime
from decimal import Decimal

from django.utils import timezone

# @formatter:off
# just don't change this unless you are living in a planet where a day takes more or less than 24 hours.
TIME_THRESHOLD_24H = timezone.now() - datetime.timedelta(hours=24)

# Default options for content object counts
TOPICS_PER_PAGE_DEFAULT = 50   # For guests only
ENTRIES_PER_PAGE_DEFAULT = 10  # For guests only
ENTRIES_PER_PAGE_PROFILE = 15  # Global setting

# Give id of the user who does administrative actions in the site. (with is_novice=False)
GENERIC_SUPERUSER_ID = 1

# Create an anonymous user with is_private=True and is_novice=False.
# This anonymous user is used to hold the entries of deleted accounts.
GENERIC_PRIVATEUSER_ID = 35

# Category related settings, don't change the current keys of NON_DB_SLUGS_SAFENAMES, they are hard-coded.
# Safenames are required for views.list.TopicList (mobile), safenames for desktop views are located in (base.html)
# with data-safename attributes.
NON_DB_SLUGS_SAFENAMES = {
    "bugun": "bugün",
    "gundem": "gündem",
    "basiboslar": "başıboşlar",
    "takip": "takip",
    "tarihte-bugun": "tarihte bugün",
    "kenar": "kenar",
    "caylaklar": "çaylaklar",
    "debe": "dünün en beğenilen entry'leri",
    "hayvan-ara": "arama sonuçları"
}


NON_DB_CATEGORIES = list(NON_DB_SLUGS_SAFENAMES.keys())

# these categories are not open to visitors
LOGIN_REQUIRED_CATEGORIES = ("bugun", "kenar", "takip")

# default category to be shown when the user requests for the first time
# should not be in LOGIN_REQUIRED_CATEGORIES
DEFAULT_CATEGORY = "debe"

# don't cache these categories
UNCACHED_CATEGORIES = ("kenar", )

YEAR_RANGE = range(2020, 2017, -1)  # for TopicList view only

# Give entry id's for flat pages.
FLATPAGE_URLS = {
    "terms-of-use": 37631,
    "privacy-policy": 37630,
    "faq": 37451,
}

SOCIAL_URLS = {
    "facebook": "https://www.facebook.com/",
    "instagram": "https://www.instagram.com/",
    "twitter": "https://twitter.com/",
}

# Used in views.json.Vote
VOTE_RATES = {
    "favorite": Decimal(".2"),
    "increase": Decimal(".2"),
    "reduce": Decimal("-.2"),
    "anonymous_multiplier": Decimal(".5"),
    "authenticated_multiplier": Decimal("1")
}

# messages
NOVICE_ACCEPTED_MESSAGE = ("sayın {}, tebrikler; yazarlık başvurunuz kabul edildi. giriş yaparak yazar olmanın"
                           " olanaklarından faydalanabilirsin.")

NOVICE_REJECTED_MESSAGE = ("sayın {}, yazarlık başvurunuz reddedildi ve tüm entryleriniz silindi. eğer 10 entry"
                           " doldurursanız tekrar çaylak onay listesine alınacaksınız.")

PASSWORD_CHANGED_MESSAGE = ("sayın {}, şifreniz değiştirildi. Eğer bu işlemden haberdar iseniz sıkıntı yok."  # nosec
                            " Bu işlemi siz yapmadıysanız, mevcut e-posta adresinizle hesabınızı kurtarabilirsiniz.")

TERMINATION_ONHOLD_MESSAGE = ("sayın {}, hesabınız donduruldu. eğer silmeyi seçtiyseniz, seçiminizden 5 gün"
                              " sonra hesabınız kalıcı olarak silinecektir. bu süre dolmadan önce hesabınıza giriş"
                              " yaptığınız takdirde hesabınız tekrar aktif hale gelecektir. eğer hesabınızı sadece"
                              " dondurmayı seçtiyseniz, herhangi bir zamanda tekrar giriş yapabilirsiniz.")
