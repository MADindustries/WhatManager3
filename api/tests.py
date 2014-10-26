from django.test.client import Client
from django.utils import timezone

from WhatManager3.test_utils import TestCase, load_fixture

from WhatManager3.utils import json_loads

from torrents.models import TorrentManager, DownloadLocation, ClientInstance, ClientTorrent
from torrents.utils import TorrentInfo
from trackers.whatcd.models import TrackerTorrent


music_info = json_loads(load_fixture('trackers/whatcd/music.json'))['response']
music_torrent_data = load_fixture('trackers/whatcd/music.torrent')


class TorrentStatusTestCase(TestCase):
    def create_instance(self):
        try:
            m = TorrentManager.objects.get()
        except TorrentManager.DoesNotExist:
            m = TorrentManager(host='0.0.0.0', port=0)
            m.save()
            DownloadLocation(path='', manager=m).save()
        i = ClientInstance(manager=m)
        i.save()
        return i

    def test_basic_status(self):
        c = Client()

        i = self.create_instance()
        info = TorrentInfo.from_binary(music_torrent_data)
        w_t = TrackerTorrent.from_response(music_info, info)
        w_t.save()

        self.assertEqual(
            json_loads(c.get('/api/torrents/status', {
                'tracker': 'what.cd',
                'ids': str(w_t.id) + ',123',
            }).content),
            {
                str(w_t.id): {
                    'status': 'missing',
                },
                '123': {
                    'status': 'missing'
                },
            }
        )

        t = ClientTorrent(announces=info.announces, info_hash=info.info_hash,
                          instance=i, location=DownloadLocation.objects.get(), size_bytes=0,
                          uploaded_bytes=0, done=0, date_added=timezone.now())
        t.save()

        self.assertEqual(
            json_loads(c.get('/api/torrents/status', {
                'tracker': 'what.cd',
                'ids': str(w_t.id) + ',123',
            }).content),
            {
                str(w_t.id): {
                    'status': 'downloading',
                    'progress': 0,
                },
                '123': {
                    'status': 'missing'
                },
            }
        )

        t.done = 0.5
        t.save()

        self.assertEqual(
            json_loads(c.get('/api/torrents/status', {
                'tracker': 'what.cd',
                'ids': str(w_t.id) + ',123',
            }).content),
            {
                str(w_t.id): {
                    'status': 'downloading',
                    'progress': 0.5,
                },
                '123': {
                    'status': 'missing'
                },
            }
        )

        t.done = 1
        t.save()

        self.assertEqual(
            json_loads(c.get('/api/torrents/status', {
                'tracker': 'what.cd',
                'ids': str(w_t.id) + ',123',
            }).content),
            {
                str(w_t.id): {
                    'status': 'downloaded',
                },
                '123': {
                    'status': 'missing'
                },
            }
        )
