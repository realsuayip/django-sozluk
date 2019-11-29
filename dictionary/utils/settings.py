import datetime
from decimal import Decimal
from django.utils import timezone

time_threshold_24h = timezone.now() - datetime.timedelta(hours=24)

TOPICS_PER_PAGE = 2  # experimental value
ENTRIES_PER_PAGE = 10
ENTRIES_PER_PAGE_PROFILE = 15

YEAR_RANGE = list(reversed(range(2017, 2020)))

banned_topics = [  # include banned topics here
    " ", "@", " % ", "seks"]


# categories
nondb_categories = ["bugun", "gundem", "basiboslar", "tarihte-bugun", "kenar", "caylaklar", "takip", "debe"]
login_required_categories = ["bugun", "kenar", "takip"]
do_not_cache = ["kenar"]

vote_rates = {"favorite": Decimal(".2"), "increase": Decimal(".2"), "reduce": Decimal("-.2"),
              "anonymous_multiplier": Decimal(".5"), "authenticated_multiplier": Decimal("1")}
