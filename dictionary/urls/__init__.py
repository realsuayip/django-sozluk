from .announcements import urlpatterns_announcements
from .auth import urlpatterns_auth
from .edit import urlpatterns_edit
from .list import urlpatterns_list
from .user import urlpatterns_user


urlpatterns = urlpatterns_announcements + urlpatterns_auth + urlpatterns_edit + urlpatterns_list + urlpatterns_user
