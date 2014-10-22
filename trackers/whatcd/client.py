import asyncio

from WhatManager3.utils import db_func
from torrents.utils import TorrentInfo
from trackers.store import TorrentStore
from trackers.whatcd.api import WhatAPI
from trackers.whatcd.models import TrackerTorrent


class TrackerClient(object):
    name = 'what.cd'
    tracker_domain = 'tracker.what.cd:34000'
    tracker_torrent_model = TrackerTorrent

    def __init__(self):
        self.client = WhatAPI.create()

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
