from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^', include('shop.urls')),
    url(r'^banks/', include('thorbanks.urls')),

    url(r'^admin/', include(admin.site.urls)),
)