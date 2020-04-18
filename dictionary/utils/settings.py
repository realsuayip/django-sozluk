from decimal import Decimal

# Default options for content object counts
TOPICS_PER_PAGE_DEFAULT = 50  # For guests only
ENTRIES_PER_PAGE_DEFAULT = 10  # For guests only
ENTRIES_PER_PAGE_PROFILE = 15  # Global setting

# Give id of the user who does administrative actions in the site. (with is_novice=False)
GENERIC_SUPERUSER_ID = 1

# Create an anonymous user with is_private=True and is_novice=False.
# This anonymous user is used to hold the entries of deleted accounts.
GENERIC_PRIVATEUSER_ID = 35

#  <-----> START OF CATEGORY RELATED SETTINGS <----->  #

# Category related settings, don't change the current keys of NON_DB_CATEGORIES_META, they are hard-coded.
# Structure: {key: (safename, description, ({"tab_slug": "tab_safename", ...}, "default_tab_slug"))...}
# dict{str:tuple(str, str, tuple(dict{str:str}, str))}
NON_DB_CATEGORIES_META = {
    "bugun": ("bugün", "en son girilenler"),
    "gundem": ("gündem", "neler olup bitiyor"),
    "basiboslar": ("başıboşlar", "kanalsız başlıklar"),
    "takip": (
        "takip",
        "takip ettiğim yazarlar ne yapmış?",
        ({"entries": "yazdıkları", "favorites": "favoriledikleri"}, "entries"),
    ),
    "ukteler": (
        "ukteler",
        "diğer yazarların entry girilmesini istediği başlıklar",
        ({"all": "hepsi", "owned": "benimkiler"}, "all"),
    ),
    "tarihte-bugun": ("tarihte bugün", "geçen yıllarda bu zamanlar ne denmiş?"),
    "kenar": ("kenar", "kenara attığım entry'ler"),
    "son": ("son", "benden sonra neler girilmiş?"),
    "caylaklar": ("çaylaklar", "çömezlerin girdikleri"),
    "debe": ("dünün en beğenilen entry'leri", "dünün en beğenilen entry'leri"),
    "hayvan-ara": ("arama sonuçları", "hayvan ara"),
}


NON_DB_CATEGORIES = tuple(NON_DB_CATEGORIES_META.keys())

# These categories have tabs. Make sure you configure metadata correctly.
TABBED_CATEGORIES = ("takip", "ukteler")

# These categories are not open to visitors
LOGIN_REQUIRED_CATEGORIES = ("bugun", "kenar", "takip", "ukteler", "caylaklar", "son")

# Cache (if enabled) these categories PER USER. (The list of objects in those categories varies on user.)
USER_EXCLUSIVE_CATEGORIES = ("bugun", "kenar", "takip", "ukteler", "son")

EXCLUDABLE_CATEGORIES = ("spor", "siyaset", "anket", "yetiskin")
"""List of category slugs (database categories) that users can opt out to see in gundem."""

# Default category to be shown when the user requests for the first time.
# Should NOT be in LOGIN_REQUIRED_CATEGORIES
DEFAULT_CATEGORY = "gundem"

DEFAULT_CACHE_TIMEOUT = 90
"""Advanced: Set default timeout for category caching."""

EXCLUSIVE_TIMEOUTS = {"debe": 86400, "tarihte-bugun": 86400, "bugun": 300, "gundem": 30}
"""Advanced: Set exclusive timeouts (seconds) for categories if you don't want them to use the default."""

# Don't cache these categories.
# (To disable a tab of a category, you can insert "categoryname_tabname", "categoryname" will affect both tabs)
UNCACHED_CATEGORIES = ("kenar", "ukteler_owned", "son")

# Set this to True to disable caching of all categories. The site will
# be more responsive & dynamic but much slower. If the website is low
# in demand, you may set this to true so that existing user base
# can interact more quickly. Consider using UNCACHED_CATEGORIES if
# you don't want to disable ALL categories.
# You may also (better) use this for debugging purposes.
DISABLE_CATEGORY_CACHING = False

# Years available for tarihte-bugun
YEAR_RANGE = (2020, 2019, 2018)

#  <-----> END OF CATEGORY RELATED SETTINGS <----->  #

"""
Generations create classification for users using their
registration date, so that users that using (or used) the site at the
same can identify each other. This also provides feedback to users
to see which users are newbies.
"""

DISABLE_GENERATIONS = False
"""Set this to True if you do not want generations to appear in profile pages."""

FIRST_GENERATION_DATE = "09.08.2019"
"""Set this to first user's registration date."""

GENERATION_GAP_DAYS = 180
"""Set the interval for seperating generations."""

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


DISABLE_ANONYMOUS_VOTING = False
"""
Set this to True to disallow anonymous votes.
Vote section will be visible to guests but they
won't have any effect.
"""

VOTE_RATES = {
    "favorite": Decimal(".2"),
    "vote": Decimal(".2"),
    "anonymous": Decimal(".05"),
}

# Messages

NOVICE_ACCEPTED_MESSAGE = (
    "sayın {}, tebrikler; yazarlık başvurunuz kabul edildi. giriş yaparak yazar olmanın"
    " olanaklarından faydalanabilirsin."
)

NOVICE_REJECTED_MESSAGE = (
    "sayın {}, yazarlık başvurunuz reddedildi ve tüm entryleriniz silindi. eğer 10 entry"
    " doldurursanız tekrar çaylak onay listesine alınacaksınız."
)

PASSWORD_CHANGED_MESSAGE = (
    "sayın {}, parolanız değiştirildi. Eğer bu işlemden haberdar iseniz sıkıntı yok."  # nosec
    " Bu işlemi siz yapmadıysanız, mevcut e-posta adresinizle hesabınızı kurtarabilirsiniz."
)

TERMINATION_ONHOLD_MESSAGE = (
    "sayın {}, hesabınız donduruldu. eğer silmeyi seçtiyseniz, seçiminizden 5 gün"
    " sonra hesabınız kalıcı olarak silinecektir. bu süre dolmadan önce hesabınıza giriş"
    " yaptığınız takdirde hesabınız tekrar aktif hale gelecektir. eğer hesabınızı sadece"
    " dondurmayı seçtiyseniz, herhangi bir zamanda tekrar giriş yapabilirsiniz."
)
