import asyncio
import os.path
from random import choice

from django.db import transaction

from WhatManager3.utils import db_func, prune_connections, json_dumps
from torrents.models import ClientTorrent, QueuedTorrent, DownloadLocation
from torrents.utils import TorrentInfo
from trackers.store import TorrentStore
from trackers.whatcd.api import WhatAPI
from trackers.whatcd.models import TrackerTorrent, FreeleechTorrent, Settings


class TrackerClient(object):
    name = 'what.cd'
    tracker_domain = 'tracker.what.cd:34000'
    tracker_torrent_model = TrackerTorrent

    def __init__(self, settings):
        self.settings = settings
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
        download_locations = DownloadLocation.get_for_tracker(self.name)
        print('Received', len(freeleech_torrents), 'freeleech torrents')
        for fl_torrent in freeleech_torrents:
            prune_connections()
            try:
                torrent = TrackerTorrent.objects.get(id=fl_torrent.torrent_id)
            except TrackerTorrent.DoesNotExist:
                torrent = yield from self.fetch_metadata(fl_torrent.torrent_id)
            try:
                ClientTorrent.objects.get(
                    announces_hash=torrent.announces_hash,
                    info_hash=torrent.info_hash
                )
            except ClientTorrent.DoesNotExist:
                download_location = choice(download_locations)
                download_path = os.path.join(download_location.path, str(torrent.id))
                try:
                    QueuedTorrent.objects.get(
                        announces_hash=torrent.announces_hash,
                        info_hash=torrent.info_hash
                    )
                except QueuedTorrent.DoesNotExist:
                    print('Queueing freeleech', torrent.id)
                    QueuedTorrent(
                        announces_hash=torrent.announces_hash,
                        info_hash=torrent.info_hash,
                        delay=0,
                        path=download_path,
                    ).save()
            yield from asyncio.sleep(0.05)

    @classmethod
    def create(cls):
        return TrackerClient(Settings.get())
