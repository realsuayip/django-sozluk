from decimal import Decimal

# @formatter:off
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
# Structure: {key: (safename, description)}
NON_DB_SLUGS_SAFENAMES = {
    "bugun": ("bugün", "en son girilenler"),
    "gundem": ("gündem", "neler olup bitiyor"),
    "basiboslar": ("başıboşlar", "kanalsız başlıklar"),
    "takip": ("takip", "takip ettiğim yazarlar ne yazmış?"),
    "tarihte-bugun": ("tarihte bugün", "geçen yıllarda bu zamanlar ne denmiş?"),
    "kenar": ("kenar", "kenara attığım entry'ler"),
    "caylaklar": ("çaylaklar", "çömezlerin girdikleri"),
    "debe": ("dünün en beğenilen entry'leri", "dünün en beğenilen entry'leri"),
    "hayvan-ara": ("arama sonuçları", "hayvan ara")
}


NON_DB_CATEGORIES = tuple(NON_DB_SLUGS_SAFENAMES.keys())

# these categories are not open to visitors
LOGIN_REQUIRED_CATEGORIES = ("bugun", "kenar", "takip", "caylaklar")

# default category to be shown when the user requests for the first time
# should not be in LOGIN_REQUIRED_CATEGORIES
DEFAULT_CATEGORY = "gundem"

# don't cache these categories
UNCACHED_CATEGORIES = ("kenar", )

YEAR_RANGE = (2020, 2019, 2018)

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
