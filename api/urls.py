from django.conf.urls import patterns, url

urlpatterns = patterns(
    '',
    url(r'^torrents/add$', 'api.views.add_torrent'),
    url(r'^torrents/delete$', 'api.views.delete_torrent'),
    url(r'^torrents/status$', 'api.views.torrents_status'),
)
