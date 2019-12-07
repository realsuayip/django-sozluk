import datetime
from decimal import Decimal
from django.utils import timezone

time_threshold_24h = timezone.now() - datetime.timedelta(hours=24)

TOPICS_PER_PAGE = 2  # experimental value
ENTRIES_PER_PAGE = 10
ENTRIES_PER_PAGE_PROFILE = 15
GENERIC_SUPERUSER_ID = 1
YEAR_RANGE = list(reversed(range(2017, 2020)))

banned_topics = ["seks", "1984"]  # include banned topics here

# categories
nondb_categories = ["bugun", "gundem", "basiboslar", "tarihte-bugun", "kenar", "caylaklar", "takip", "debe"]
login_required_categories = ["bugun", "kenar", "takip"]
do_not_cache = ["kenar"]

vote_rates = {"favorite": Decimal(".2"), "increase": Decimal(".2"), "reduce": Decimal("-.2"),
              "anonymous_multiplier": Decimal(".5"), "authenticated_multiplier": Decimal("1")}

# messages
application_accept_message = "sayın {}, tebrikler; yazarlık başvurunuz kabul edildi. giriş yaparak yazar olmanın " \
                             "olanaklarından faydalanabilirsin."
application_decline_message = 'sayın {}, yazarlık başvurunuz reddedildi ve tüm entryleriniz silindi. eğer 10 entry ' \
                              'doldurursanız tekrar çaylak onay listesine alınacaksınız.'
