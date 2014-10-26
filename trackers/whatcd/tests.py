import asyncio
import os
import os.path
import shutil
from unittest import mock

from WhatManager3.test_utils import TestCase, load_fixture
from WhatManager3.utils import json_loads
from trackers.store import TorrentStore
from trackers.whatcd.client import TrackerClient
from trackers.whatcd.models import TrackerTorrent, TorrentGroup, Artist, ArtistAlias, TorrentArtist, \
    Settings


def _read_fixture(filename):
    return load_fixture('trackers/whatcd/{}'.format(filename))


music_json = _read_fixture('music.json')
application_json = _read_fixture('application.json')
ebook_json = _read_fixture('ebook.json')
audiobook_json = _read_fixture('audiobook.json')
elearn_video_json = _read_fixture('elearn_video.json')
comedy_json = _read_fixture('comedy.json')
comic_json = _read_fixture('comic.json')

music_torrent_data = _read_fixture('music.torrent')


class MockWhatAPI():
    def __init__(self):
        self.torrents = {}
        for resp in [music_json, application_json, ebook_json, audiobook_json, elearn_video_json,
                     comedy_json, comic_json]:
            resp_data = json_loads(resp)['response']
            self.torrents[resp_data['torrent']['id']] = resp_data

    @asyncio.coroutine
    def request(self, action, **kwargs):
        if action == 'torrent':
            return self.torrents[kwargs['id']]
        else:
            raise NotImplementedError()

    @asyncio.coroutine
    def get_torrent(self, torrent_id):
        return 'no_file.torrent', music_torrent_data


@mock.patch('WhatManager3.utils.prune_connections', lambda: None)
@mock.patch('trackers.whatcd.client.WhatAPI', lambda a, b: MockWhatAPI())
class TrackerTorrentTestCase(TestCase):
    def setUp(self):
        store = TorrentStore.create()
        self.assertEqual(os.listdir(store.dir), ['.gitignore'],
                         'Failing to run with a non-empty torrent store')

    def tearDown(self):
        store = TorrentStore.create()
        for item in os.listdir(store.dir):
            if item[0] == '.':
                continue
            shutil.rmtree(os.path.join(store.dir, item))

    def create_tracker_client(self):
        return TrackerClient(Settings(
            user_id=0,
            username='',
            password='',
            monitor_freeleech=False
        ))

    def test_create_music_torrent(self):
        client = self.create_tracker_client()
        music_torrent = asyncio.get_event_loop().run_until_complete(client.fetch_metadata(31720330))
        self.assertEqual(music_torrent.id, 31720330)
        self.assertEqual(music_torrent.info_hash, '5F1C7A60FFA607E24375421EC08683533E3774FE')
        self.assertEqual(music_torrent.info.category_id, 1)
        self.assertEqual(music_torrent.info.release_type_id, 1)
        self.assertEqual(music_torrent.info.media, 'CD')
        self.assertEqual(music_torrent.info.format, 'FLAC')
        self.assertEqual(music_torrent.info.encoding, 'Lossless')
        self.assertEqual(music_torrent.info.joined_artists, 'Led Zeppelin')
        self.assertEqual(music_torrent.info.size, 559936095)
        TrackerTorrent.objects.get(id=31720330)
        self.assertEqual(Artist.objects.all().count(), 4)
        self.assertEqual(TorrentGroup.objects.get().trackertorrent_set.get().id, 31720330)

    def test_delete(self):
        client = self.create_tracker_client()
        music_torrent = asyncio.get_event_loop().run_until_complete(client.fetch_metadata(31720330))
        music_torrent.delete()
        self.assertEqual(TrackerTorrent.objects.count(), 0)
        self.assertEqual(TorrentGroup.objects.count(), 0)
        self.assertEqual(TorrentArtist.objects.count(), 0)
        self.assertEqual(Artist.objects.count(), 0)
        self.assertEqual(ArtistAlias.objects.count(), 0)

    def test_create_application_torrent(self):
        client = self.create_tracker_client()
        asyncio.get_event_loop().run_until_complete(client.fetch_metadata(31720561))
        tg = TorrentGroup.objects.get()
        self.assertEqual(tg.trackertorrent_set.get().id, 31720561)
        self.assertEqual(tg.name, 'Audirvana Plus 2.0.2 [Intel/K\'ed]')

    def test_ebook_torrent(self):
        client = self.create_tracker_client()
        asyncio.get_event_loop().run_until_complete(client.fetch_metadata(31720103))
        tg = TorrentGroup.objects.get()
        self.assertEqual(tg.trackertorrent_set.get().id, 31720103)
        self.assertEqual(tg.name, 'Chuck Palahniuk - Rant: An Oral Biography of Buster Casey')

    def test_audiobook_torrent(self):
        client = self.create_tracker_client()
        asyncio.get_event_loop().run_until_complete(client.fetch_metadata(31720450))
        tg = TorrentGroup.objects.get()
        self.assertEqual(tg.trackertorrent_set.get().id, 31720450)
        self.assertEqual(tg.name, 'Michael Rank - From Muhammed to Burj Khalifa: A Crash Course in'
                                  ' 2,000 Years of Middle East History')

    def test_elearn_video_torrent(self):
        client = self.create_tracker_client()
        asyncio.get_event_loop().run_until_complete(client.fetch_metadata(31720559))
        tg = TorrentGroup.objects.get()
        self.assertEqual(tg.trackertorrent_set.get().id, 31720559)
        self.assertEqual(tg.name, 'Groove3.Turnado.Explained')

    def test_comedy_torrent(self):
        client = self.create_tracker_client()
        asyncio.get_event_loop().run_until_complete(client.fetch_metadata(31718839))
        tg = TorrentGroup.objects.get()
        self.assertEqual(tg.trackertorrent_set.get().id, 31718839)
        self.assertEqual(tg.name, 'The Goons - The Goons: Volume 2')

    def test_comic_torrent(self):
        client = self.create_tracker_client()
        asyncio.get_event_loop().run_until_complete(client.fetch_metadata(31720617))
        tg = TorrentGroup.objects.get()
        self.assertEqual(tg.trackertorrent_set.get().id, 31720617)
        self.assertEqual(tg.name, 'Prison Pit - Book Three')
