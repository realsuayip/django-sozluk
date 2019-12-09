import datetime
from decimal import Decimal
from django.utils import timezone

# just don't change this unless you are living in a planet where a day takes more or less than 24 hours.
TIME_THRESHOLD_24H = timezone.now() - datetime.timedelta(hours=24)

TOPICS_PER_PAGE = 2  # experimental value
ENTRIES_PER_PAGE = 10  # except authenticated users
ENTRIES_PER_PAGE_PROFILE = 15
GENERIC_SUPERUSER_ID = 1


# include banned topics here, more useful if you want to create a static page with some text like 'terms & conditions'
BANNED_TOPICS = ["seks", "1984"]

# category related settings, don't change the keys of NON_DB_SLUGS_SAFENAMES, they are hard-coded. but:
# if you really have to change that, related files are: views.list.TopicList, views.json.AsyncTopicList,
# utils.managers.TopicListManager and bunch of html files with djdict.js
# safenames are required for views.list.TopicList (mobile), safenames for desktop views are located in html (base.html)
# with data-safename attributes
NON_DB_SLUGS_SAFENAMES = {"bugun": "bugün", "gundem": "gündem", "basiboslar": "başıboşlar", "takip": "takip",
                          "tarihte-bugun": "tarihte bugün", "kenar": "kenar", "caylaklar": "çaylaklar",
                          "debe": "dünün en beğenilen entry'leri", "hayvan-ara": "arama sonuçları"}

NON_DB_CATEGORIES = list(NON_DB_SLUGS_SAFENAMES.keys())
LOGIN_REQUIRED_CATEGORIES = ["bugun", "kenar", "takip"]  # these categories are not open to visitors
UNCACHED_CATEGORIES = ["kenar", "hayvan-ara"]  # don't cache these categories
SINGLEPAGE_CATEGORIES = ["debe", "hayvan-ara"]  # these categories only show 1 page of data
YEAR_RANGE = list(reversed(range(2017, 2020)))  # for mobile only

# Used in views.json.Vote
VOTE_RATES = {"favorite": Decimal(".2"), "increase": Decimal(".2"), "reduce": Decimal("-.2"),
              "anonymous_multiplier": Decimal(".5"), "authenticated_multiplier": Decimal("1")}

NOVICE_ACCEPTED_MESSAGE = "sayın {}, tebrikler; yazarlık başvurunuz kabul edildi. giriş yaparak yazar olmanın " \
                          "olanaklarından faydalanabilirsin."
NOVICE_REJECTED_MESSAGE = 'sayın {}, yazarlık başvurunuz reddedildi ve tüm entryleriniz silindi. eğer 10 entry ' \
                          'doldurursanız tekrar çaylak onay listesine alınacaksınız.'
