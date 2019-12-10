from .auth import urlpatterns_auth
from .edit import urlpatterns_edit
from .json import urlpatterns_json
from .list import urlpatterns_list
from .user import urlpatterns_user

urlpatterns = urlpatterns_auth + urlpatterns_edit + urlpatterns_json + urlpatterns_list + urlpatterns_user
