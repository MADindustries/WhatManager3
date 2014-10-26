from django.conf.urls import patterns, url

from api.views import add_torrent, delete_torrent, torrents_status, site_stats, torrents_store_get
from api.whatcd.views import get_freeleech_torrents


urlpatterns = patterns(
    '',
    url(r'^torrents/add$', add_torrent),
    url(r'^torrents/delete$', delete_torrent),
    url(r'^torrents/status$', torrents_status),
    url(r'^torrents/store/get$', torrents_store_get),
    url(r'^stats$', site_stats),

    url(r'^whatcd/torrents/freeleech', get_freeleech_torrents),
)
