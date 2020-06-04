from decimal import Decimal

DOMAIN = "xyzsozluk.com"
PROTOCOL = "http"
FROM_EMAIL = "noreply@xyzsozluk.org"

# Default options for content object counts
TOPICS_PER_PAGE_DEFAULT = 50  # For guests only
ENTRIES_PER_PAGE_DEFAULT = 10  # For guests only
ENTRIES_PER_PAGE_PROFILE = 15  # Global setting


GENERIC_SUPERUSER_USERNAME = "djangosozluk"
"""
Give the username of the user who does administrative actions in the site.
"""

GENERIC_PRIVATEUSER_USERNAME = "anonymous"
"""
Create an anonymous user with is_private=True and is_novice=False.
This anonymous user is used to hold the entries of deleted accounts.
"""

#  <-----> START OF CATEGORY RELATED SETTINGS <----->  #


NON_DB_CATEGORIES_META = {
    "today": ("bugün", "en son girilenler"),
    "popular": ("gündem", "neler olup bitiyor"),
    "uncategorized": ("başıboşlar", "kanalsız başlıklar"),
    "acquaintances": (
        "takip",
        "takip ettiğim yazarlar ne yapmış?",
        ({"entries": "yazdıkları", "favorites": "favoriledikleri"}, "entries"),
    ),
    "wishes": (
        "ukteler",
        "diğer yazarların entry girilmesini istediği başlıklar",
        ({"all": "hepsi", "owned": "benimkiler"}, "all"),
    ),
    "today-in-history": ("tarihte bugün", "geçen yıllarda bu zamanlar ne denmiş?"),
    "drafts": ("kenar", "kenara attığım entry'ler"),
    "followups": ("son", "benden sonra neler girilmiş?"),
    "novices": ("çaylaklar", "çömezlerin girdikleri"),
    "top": ("dünün en beğenilen entry'leri", "debe"),
    "search": ("arama sonuçları", "hayvan ara"),
    "userstats": (
        "kullanıcı istatistiği",
        "kullanıcı istatistiği",
        (
            {
                "latest": "@{} - entryleri",
                "popular": "@{} - en çok favorilenenleri",
                "favorites": "@{} - favorileri",
                "recentlyvoted": "@{} - son oylananları",
                "liked": "@{} - en beğenilenleri",
                "weeklygoods": "@{} - bu hafta dikkat çekenleri",
                "beloved": "@{} - el emeği göz nuru",
                "channels": "@{} - #{} başlıkları",
            },
            "latest",
        ),
    ),
}
"""
Category related settings. Notice: The current keys of NON_DB_CATEGORIES_META are hard-coded.
Structure: dict{str:tuple(str, str, tuple(dict{str:str}, str))}

{key: (safename, description, ({"tab_slug": "tab_safename", ...}, "default_tab_slug"))...}
"""

NON_DB_CATEGORIES = NON_DB_CATEGORIES_META.keys()
"""Don't touch. For internal use only."""

TABBED_CATEGORIES = ("acquaintances", "wishes", "userstats")
"""These categories have tabs. Make sure you configure metadata correctly."""

USER_EXCLUSIVE_CATEGORIES = ("today", "drafts", "acquaintances", "wishes", "followups")
"""Cache (if enabled) these categories PER USER (The list of objects in those categories varies on user)."""

LOGIN_REQUIRED_CATEGORIES = USER_EXCLUSIVE_CATEGORIES + ("novices",)
"""These categories are not open to visitors."""

EXCLUDABLE_CATEGORIES = ("spor", "siyaset", "anket", "yetiskin")
"""List of category slugs (database categories) that users can opt out to see in popular."""

DEFAULT_CATEGORY = "popular"
"""
Default category to be shown when the user requests for the first time.
Should NOT be in LOGIN_REQUIRED_CATEGORIES.
"""

PARAMETRIC_CATEGORIES = ("userstats",)  # intended for developers
"""
ADVANCED: These categories use many parameters. These parameters will be dumped
and read from TopicListManager's 'extra'. If you're extending TopicEntryList and
want to make use of parameters, you should probably use this. You can use
_set_internal_extra of TopicEntryList to add or modify extras for any category.
Extras can only be of str type.

Available internal extras:
    safename (overrides safename of the category)
    hidetabs (hides tabs for tabbed categories if set to 'yes')

Available external extras:
    user    (a username)
    channel (a channel name)

Graph takes extras using JSONString, in mobile, extras given via query params.
You may add any number of external/internal extras, I made this so that
adding further params wouldn't require too much change in code / break old code.
"""

DEFAULT_CACHE_TIMEOUT = 90
"""ADVANCED: Set default timeout for category caching."""

EXCLUSIVE_TIMEOUTS = {"top": 86400, "today-in-history": 86400, "today": 300, "popular": 30}
"""ADVANCED: Set exclusive timeouts (seconds) for categories if you don't want them to use the default."""


UNCACHED_CATEGORIES = ("drafts", "wishes_owned", "followups")
"""
Don't cache these categories.
To disable a tab of a category, you can insert "categoryname_tabname", "categoryname" will affect all tabs.
"""

DISABLE_CATEGORY_CACHING = False
"""
Set this to True to disable caching of all categories. The site will
be more responsive & dynamic but much slower. If the website is low
in demand, you may set this to true so that existing user base
can interact more quickly. Consider using UNCACHED_CATEGORIES if
you don't want to disable ALL categories.
You may also (better) use this for debugging purposes.
"""


YEAR_RANGE = (2020, 2019, 2018)
"""Years available for today-in-history"""

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


DISABLE_ANONYMOUS_VOTING = False
"""
Set this to True to disallow anonymous votes.
Vote section will be visible to guests but they
won't have any effect.
"""

# Notice: Decimal places larger than 2 is not allowed. e.g. 0.125 is not valid.

VOTE_RATES = {
    "favorite": Decimal(".2"),      # The amount of rate an entry will get when favorited.
    "vote": Decimal(".2"),          # The amount of rate to be deducted/added when entry gets voted.
    "anonymous": Decimal(".05"),    # Same with vote, but for anonymous users.
}

# Karma related settings

KARMA_RATES = {
    "upvote": Decimal("0.18"),      # The amount of karma that the user will gain upon getting an upvote.
    "downvote": Decimal("0.27"),    # The amount of karma that the user will lose upon getting an downvote.
    "cost": Decimal("0.09"),        # The amount of karma that the user will lose upon voting an entry.
}

DAILY_VOTE_LIMIT = 240
"""The total number of entries that a user can vote in a 24 hour period."""

DAILY_VOTE_LIMIT_PER_USER = 24
"""Same with daily vote limit but applies for one author. E.g. author X
can only vote 24 entries of author Y"""

TOTAL_VOTE_LIMIT_PER_USER = 160
"""Similar to daily vote limit per user, but considers all time votes."""

KARMA_EXPRESSIONS = {
    range(25, 50): "kaotik nötral",
    range(50, 100): "müzmin yedek",
    range(100, 125): "padawan",
    range(125, 150): "çılgın",
    range(150, 200): "kofti anarşist",
    range(200, 250): "anarşist",
    range(250, 300): "hırçın golcü",
    range(300, 350): "anadolu çocuğu",
    range(350, 370): "battal gazi",
    range(370, 400): "çetrefilli",
    range(400, 430): "hippi",
    range(430, 450): "delikanlı",
    range(450, 470): "ağır abi",
    range(470, 500): "bıçkın",
    range(500, 530): "mangal yürekli rişar",
    range(530, 550): "mülayim ama sempatik",
    range(550, 575): "aklı selim",
    range(575, 600): "prezentabl",
    range(600, 620): "şeker abi",
    range(620, 630): "bal küpü",
    range(630, 650): "baldan tatlı",
    range(650, 665): "leziz",
    range(665, 680): "entry uğruna ruhunu satmış",
    range(680, 700): "şekerpare",
    range(700, 725): "şamda kayısı",
    range(725, 750): "her eve lazım",
    range(750, 775): "tadına doyum olmaz",
    range(775, 800): "energizer tavşanı",
    range(800, 850): "gençlerin sevgilisi",
    range(850, 900): "fevkalbeşer",
    range(900, 1000): "rating canavarı",
}
"""
Karma expressions for specific karma ranges. All expressions are
excerpted from ekşi sözlük. Their rights might be reserved.
"""

KARMA_BOUNDARY_UPPER = 1000
"""
Karma points required to earn the overwhelming karma expression.
Notice: This number must be the stop parameter of the largest range item in
KARMA_EXPRESSIONS, otherwise the flair won't be visible for those who have
more than max specified in KARMA_EXPRESSIONS but less than KARMA_BOUNDARY_UPPER.
"""

KARMA_BOUNDARY_LOWER = -200
"""
Karma points required to be given the underwhelming karma expression.
Also, if an user has has such karma, they won't be able to influence
other people's karma by voting.
"""

UNDERWHELMING_KARMA_EXPRESSION = "geri zekâlı"
"""Expression for too low karma points. (decided by KARMA_BOUNDARY_LOWER)"""

OVERWHELMING_KARMA_EXPRESSION = "halkın şampiyonu"
"""Expression for too high karma points. (decided by KARMA_BOUNDARY_UPPER)"""

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
