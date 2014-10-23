import asyncio
import time

from django.db import transaction

from WhatManager3.utils import db_func, prune_connections, json_dumps
from torrents.utils import TorrentInfo
from trackers.store import TorrentStore
from trackers.whatcd.api import WhatAPI
from trackers.whatcd.models import TrackerTorrent, FreeleechTorrent, Settings


class TrackerClient(object):
    name = 'what.cd'
    tracker_domain = 'tracker.what.cd:34000'
    tracker_torrent_model = TrackerTorrent

    def __init__(self):
        self.settings = Settings.get()
        self.client = WhatAPI(self.settings.username, self.settings.password)

    @asyncio.coroutine
    @db_func
    def fetch_metadata(self, torrent_id):
        store = TorrentStore.create()
        response = yield from self.client.request('torrent', id=torrent_id)
        _, torrent_data = yield from self.client.get_torrent(torrent_id)
        info = TorrentInfo.from_binary(torrent_data)
        store.put(torrent_data)
        torrent = TrackerTorrent.from_response(response, info)
        torrent.save()
        return torrent

    @asyncio.coroutine
    def update_freeleech(self):
        if not self.settings.monitor_freeleech:
            return
        groups = yield from self.client.get_browse_results(freetorrent=1)
        prune_connections()
        with transaction.atomic():
            FreeleechTorrent.objects.all().delete()
            for group in groups:
                torrents = group.pop('torrents', [])
                for api_torrent in torrents:
                    if not api_torrent['isFreeleech']:
                        continue
                    torrent = FreeleechTorrent(
                        group_id=group['groupId'],
                        torrent_id=api_torrent['torrentId'],
                        group_json=json_dumps(group),
                        torrent_json=json_dumps(api_torrent)
                    )
                    torrent.save()
        yield from self.update_freeleech_metadata()

    @asyncio.coroutine
    def update_freeleech_metadata(self):
        prune_connections()
        freeleech_torrents = list(FreeleechTorrent.objects.all())
        for torrent in freeleech_torrents:
            prune_connections()
            try:
                print('Checking', torrent.torrent_id)
                s = time.time()
                TrackerTorrent.objects.get(id=torrent.torrent_id)
            except TrackerTorrent.DoesNotExist:
                yield from self.fetch_metadata(torrent.torrent_id)
            else:
                yield from asyncio.sleep(0.05)
        print('freeleech metadata complete')
