from django.conf.urls import patterns, url
from django.contrib.auth.views import login, logout

from home.views import dashboard


urlpatterns = patterns(
    '',
    url(r'^$', dashboard),
    url(r'^accounts/login/$', view=login, name='login'),
    url(r'^accounts/logout/$', view=logout, kwargs={'next_page': '/'}, name='logout'),
)
