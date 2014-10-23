from django.conf.urls import patterns, url

from api.views import add_torrent, delete_torrent, torrents_status, site_stats


urlpatterns = patterns(
    '',
    url(r'^torrents/add$', add_torrent),
    url(r'^torrents/delete$', delete_torrent),
    url(r'^torrents/status$', torrents_status),
    url(r'^stats$', site_stats),
)
