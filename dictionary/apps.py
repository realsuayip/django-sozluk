from decimal import Decimal

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


# pylint: disable=C0415,W0611
class DictionaryConfig(AppConfig):
    name = "dictionary"
    verbose_name = _("Dictionary")

    def ready(self):
        import dictionary.signals  # noqa

    # Settings

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

    DISABLE_NOVICE_QUEUE = False
    """
    When set to True, users registered via 'registration form' will be authors
    immediately, skipping the necessity of writing 10 entries and waiting for
    the approval of mods/admins.
    """

    INDEX_TYPE = "random_records"
    """
    What type of records do we want in index? (nice_records, random_records),
    cache timeout, queryset size and nice boundary can be found in views.list.Index
    """

    #  <-----> START OF CATEGORY RELATED SETTINGS <----->  #

    NON_DB_CATEGORIES_META = {
        "today": (_("today"), _("most recent entries")),
        "popular": (_("popular"), _("whats happening?")),
        "uncategorized": (_("uncategorized"), _("topics with no channels")),
        "acquaintances": (
            _("acquaintances"),
            _("what are users i follow up to?"),
            ({"entries": _("entries"), "favorites": _("favorites")}, "entries"),
        ),
        "wishes": (
            _("wishes"),
            _("the topics that some authors want populated"),
            ({"all": _("all"), "owned": _("owned")}, "all"),
        ),
        "today-in-history": (_("today in history"), _("what has been said around this time in the past years?")),
        "drafts": (_("drafts"), _("the entries that i've yet to publish")),
        "followups": (_("followups"), _("what other authors wrote down after me?")),
        "novices": (_("novices"), _("the entries of novice users")),
        "top": (
            _("top"),
            _("most liked entries"),
            ({"yesterday": _("yesterday"), "week": _("last week")}, "yesterday"),
        ),
        "search": (_("search"), _("advanced search")),
        "userstats": (
            _("user statistics"),
            _("user statistics"),
            (
                {
                    "latest": _("@%(username)s - entries"),
                    "popular": _("@%(username)s - most favorited"),
                    "favorites": _("@%(username)s - favorites"),
                    "recentlyvoted": _("@%(username)s - recently voted"),
                    "liked": _("@%(username)s - most liked"),
                    "weeklygoods": _("@%(username)s - attracting entries of this week"),
                    "beloved": _("@%(username)s - beloved entries"),
                    "channels": _("@%(username)s - #%(channel)s topics"),
                },
                "latest",
            ),
        ),
        "ama": (_("ama"), _("question-and-answer themed interactive interviews")),
    }
    """
    Category related settings. Notice: Some keys of NON_DB_CATEGORIES_META are
    hard-coded. Structure: dict{str:tuple(str, str, tuple(dict{str:str}, str))}
    Semantic: {key: (safename, description, ({"tab_slug": "tab_safename", ...}, "default_tab_slug"))...}

    Notice: In default setup, "ama" is accessible with links but there is no
    reference in header (or in any of the templates). You need to adjust that
    yourself in templates.

    If you want some category to be inaccessible in the website, you can safely
    remove it from NON_DB_CATEGORIES_META (some template references might
    need to be removed as well depending on the category).
    """

    NON_DB_CATEGORIES = NON_DB_CATEGORIES_META.keys()
    """Don't touch. For internal use only."""

    TABBED_CATEGORIES = ("acquaintances", "wishes", "userstats", "top")
    """
    These categories have tabs. Make sure you configure metadata correctly.
    """

    USER_EXCLUSIVE_CATEGORIES = ("today", "drafts", "acquaintances", "wishes", "followups")
    """
    Cache (if enabled) these categories PER USER (The list of objects in those
    categories varies on authenticated user).
    """

    LOGIN_REQUIRED_CATEGORIES = USER_EXCLUSIVE_CATEGORIES + ("novices",)
    """These categories are not open to visitors."""

    EXCLUDABLE_CATEGORIES = ("spor", "siyaset", "anket", "yetiskin")
    """
    List of category slugs (database categories) that users can opt out to
    see in popular.
    """

    DEFAULT_EXCLUSIONS = ["yetiskin"]
    """
    List of category slugs (database categories) that will be excluded in popular
    by default. (When a user requests the site for the first time.) If you don't
    want anything to be excluded by default, leave it blank: []
    """

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
        generic_category (Category object -when user requests a generic category-)

    Available external extras (cacheable):
        user    (slug)
        channel (slug)

    Graph takes extras using JSONString, in mobile, extras given via query params.
    You may add any number of external/internal extras, I made this so that
    adding further params wouldn't require too much change in code / break old code.

    Don't verify external extras' values that have space in it, values are used in
    cache keys and space char is forbidden in memcached. Best would be taking slug
    and making queries to get the actual object in _set_internal_extra.
    """

    DEFAULT_CACHE_TIMEOUT = 90
    """ADVANCED: Set default timeout for category caching."""

    EXCLUSIVE_TIMEOUTS = {"top": 86400, "today-in-history": 86400, "today": 300, "popular": 30}
    """
    ADVANCED: Set exclusive timeouts (seconds) for categories if you don't want
    them to use the default.
    """

    REFRESH_TIMEOUT = 0.1337
    """
    ADVANCED: For 'today', set the timeout for refresh interval. (This also sets
    the delimiter for manual cache deleting when delimiter is set to True.)
    Can be type of int or float.

    Notice: Intentionally set low because of development purposes! 30 should be
    fine for production.
    """

    UNCACHED_CATEGORIES = ("drafts", "wishes_owned", "followups")
    """
    Don't cache these categories.
    To disable a tab of a category, you can insert "categoryname_tabname",
    "categoryname" will affect all tabs.
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

    DISABLE_GENERATIONS = False
    """
    Set this to True if you do not want generations to appear in profile pages.

    Generations create classification for users using their
    registration date, so that users that using (or used) the site at the
    same can identify each other. This also provides feedback to users
    to see which users are newbies.
    """

    FIRST_GENERATION_DATE = "13.08.2019"
    """Set this to first user's registration date. (day should be first)"""

    GENERATION_GAP_DAYS = 180
    """Set the interval for seperating generations."""

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
    """
    favorite: The amount of rate an entry will get when favorited.
    vote: The amount of rate to be deducted/added when entry gets voted.
    anonymous: Same with vote, but for anonymous users.

    Notice: Decimal places larger than 2 is not allowed. e.g. 0.125 is not
    valid. (Likewise in KARMA_RATES)
    """

    # Karma related settings

    KARMA_RATES = {
        "upvote": Decimal("0.18"),
        "downvote": Decimal("0.27"),
        "cost": Decimal("0.09"),
    }
    """
    upvote: The amount of karma that the user will gain upon getting an upvote.
    downvote: The amount of karma that the user will lose upon getting an downvote.
    cost: The amount of karma that the user will lose upon voting an entry.
    """

    DAILY_VOTE_LIMIT = 240
    """The total number of entries that a user can vote in a 24 hour period."""

    DAILY_VOTE_LIMIT_PER_USER = 24
    """
    Same with daily vote limit but applies for one author. E.g. author X
    can only vote 24 entries of author Y
    """

    TOTAL_VOTE_LIMIT_PER_USER = 160
    """Similar to daily vote limit per user, but considers all time votes."""

    KARMA_EXPRESSIONS = {
        range(25, 50): _("chaotic neutral"),
        range(50, 100): _("chronic backup"),
        range(100, 125): _("padawan"),
        range(125, 150): _("lunatic"),
        range(150, 200): _("fragile anarchist"),
        range(200, 250): _("anarchist"),
        range(250, 300): _("turbulent kicker"),
        range(300, 350): _("anatolian boy"),
        range(350, 370): _("battal gazi"),
        range(370, 400): _("thorny"),
        range(400, 430): _("hippy"),
        range(430, 450): _("lad"),
        range(450, 470): _("staid"),
        range(470, 500): _("rowdy"),
        range(500, 530): _("richard the blazeheart "),
        range(530, 550): _("compliant yet sympathetic"),
        range(550, 575): _("right minded"),
        range(575, 600): _("presentable"),
        range(600, 620): _("sugar"),
        range(620, 630): _("honeypot"),
        range(630, 650): _("yummier honey"),
        range(650, 665): _("luscious"),
        range(665, 680): _("addicted"),
        range(680, 700): _("switheet"),
        range(700, 725): _("damascus apricot"),
        range(725, 750): _("household"),
        range(750, 775): _("exuberant"),
        range(775, 800): _("energizer bunny"),
        range(800, 850): _("courteous"),
        range(850, 900): _("inhuman"),
        range(900, 1000): _("rating beast"),
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
    Also, if a user has has such karma, they won't be able to influence
    other people's karma by voting.
    """

    UNDERWHELMING_KARMA_EXPRESSION = _("imbecile")
    """Expression for too low karma points. (decided by KARMA_BOUNDARY_LOWER)"""

    OVERWHELMING_KARMA_EXPRESSION = _("the champion")
    """Expression for too high karma points. (decided by KARMA_BOUNDARY_UPPER)"""

    # Suggestions

    SUGGESTIONS_PER_TOPIC = 3
    """Number of suggestions a user can make per topic."""

    SUGGESTIONS_PER_DAY = 45
    """Number of suggestions users can make in a 24 hour period."""

    SUGGESTIONS_QUALIFY_RATE = 3
    """
    Rate which qualifies a channel for a topic, e.g. AT LEAST this many users
    should agree to qualify a channel.
    """

    SUGGESTIONS_ENTRY_REQUIREMENT = 100
    """The number of entries required to acquire the privilege of suggesting channels."""

    # Images

    MAX_UPLOAD_SIZE = 1048576 * 2.5
    """
    1MB = 1048576 bytes.
    a) You also need to change this setting in frontend, e.g. dropzone settings
    in editor.js

    b) By default Nginx client_max_body_size is 1M, so you also need do set
    it properly.
    """

    DAILY_IMAGE_UPLOAD_LIMIT = 25
    """
    In a 24 hour period, users will be able to upload this many files at most.
    """

    COMPRESS_IMAGES = False
    """
    Set True to enable image compression according to subsequent settings while uploading.
    Notice: GIFs are not supported, they will lose animations.
    """

    COMPRESS_THRESHOLD = 2621440  # 2.5MB
    """
    Images with size bigger than this will get compressed, set to 1 to always compress.
    """

    COMPRESS_QUALITY = 70
    """
    Compression quality. The higher the better quality but more in size.
    (Integer from 1 to 95.)
    """

    XSENDFILE_HEADER_NAME = "X-Accel-Redirect"
    """
    Nginx only. Apache counterpart is 'X-Sendfile' which requires mod_xsendfile.
    """

    MESSAGE_PURGE_THRESHOLD = 300  # 5 minutes
    """
    After this many seconds, the message will be deleted for the sender
    only (instead of both users).
    """

    AUTHOR_ENTRY_INTERVAL = 0
    """Time interval for publishing entries (seconds)."""

    NOVICE_ENTRY_INTERVAL = 0
    """Same with above, but for novices."""
