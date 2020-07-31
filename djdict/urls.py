"""djdict URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.sitemaps import views as sitemap_views
from django.urls import include, path
from django.views.decorators.gzip import gzip_page
from django.views.i18n import JavaScriptCatalog

from dictionary.sitemaps import sitemaps


urlpatterns = [
    path("", include("dictionary.urls")),
    path("graphql/", include("dictionary_graph.urls")),
    path("admin/", admin.site.urls),
    # i18n
    path("jsi18n/", JavaScriptCatalog.as_view(packages=["dictionary"]), name="javascript-catalog"),
    path("i18n/", include("django.conf.urls.i18n")),
    # Sitemap
    path("sitemap.xml", gzip_page(sitemap_views.index), {"sitemaps": sitemaps}),
    path(
        "sitemap-<section>.xml",
        gzip_page(sitemap_views.sitemap),
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
]

# Will consider this near release:
# https://docs.djangoproject.com/en/3.0/topics/i18n/translation/#note-on-performance
