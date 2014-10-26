import asyncio
from unittest import TestCase as NoDBTestCase

# Create your tests here.
from django.test.testcases import TestCase
from django.utils import timezone
from torrents import bencode
from torrents.manager.sharding import choose_shard, TorrentAlreadyAddedException
from torrents.models import ClientTorrent, ClientInstance, TorrentManager, DownloadLocation
from torrents.utils import encode_announces, decode_announces, TorrentInfo

from WhatManager3.utils import load_fixture


def _load_fixture(filename):
    return load_fixture('torrents/{}'.format(filename))


what_torrent_data = _load_fixture('what.torrent')
multi_tracker_data = _load_fixture('multi_tracker.torrent')


class BencodeTestCase(NoDBTestCase):
    def test_rountrip(self):
        data = {
            b'list': [1, 2, 3],
            b'bool': True,
            b'string': b'blooblah'
        }
        bencoded = bencode.bencode(data)
        bdecoded = bencode.bdecode(bencoded)
        bencoded2 = bencode.bencode(bdecoded)
        self.assertEqual(bencoded, bencoded2)


class AnnounceEncodingTestCase(NoDBTestCase):
    def test_roundtrip(self):
        self.encode_decode([['hi']])
        self.encode_decode([['hi', 'boo']])
        self.encode_decode([['hi', 'boo']])
        self.encode_decode([['hi', 'boo'], ['hi2']])
        self.encode_decode([['hi', 'boo'], ['hi2', 'boo2']])

    def encode_decode(self, data):
        encoded = encode_announces(data)
        decoded = decode_announces(encoded)
        self.assertEqual(data, decoded)


class TorrentInfoTestCase(NoDBTestCase):
    def do_test_parsing(self, b):
        info = TorrentInfo.from_binary(b)
        torrent = ClientTorrent()
        torrent.announces = info.announces
        self.assertEqual(torrent.announces, info.announces)
        self.assertEqual(torrent.announces_hash, info.announces_hash)
        return info

    def test_parsing_single(self):
        self.do_test_parsing(what_torrent_data)

    def test_parsing_multiple(self):
        info = self.do_test_parsing(multi_tracker_data)
        self.assertEqual(info.announces, [['http://a1', 'http://a2']])


class ShardingTestCase(TestCase):
    def setUp(self):
        self.info = TorrentInfo.from_binary(what_torrent_data)

    def choose_shard(self, locked_instances):
        return choose_shard(locked_instances, self.info.announces_hash, self.info.info_hash)

    def create_instance(self):
        try:
            m = TorrentManager.objects.get()
        except TorrentManager.DoesNotExist:
            m = TorrentManager(host='0.0.0.0', port=0)
            m.save()
            DownloadLocation(path='', manager=m).save()
        i = ClientInstance(manager=m)
        i.lock = asyncio.Lock()
        i.save()
        return i

    def test_no_instances(self):
        self.assertRaisesMessage(
            Exception, 'No instances are available',
            lambda: self.choose_shard([])
        )
        i = self.create_instance()
        t = ClientTorrent(announces=[['a']], info_hash=self.info.info_hash,
                          instance=i, location=DownloadLocation.objects.get(), size_bytes=0,
                          uploaded_bytes=0, done=1, date_added=timezone.now())
        t.save()
        self.assertRaisesMessage(
            Exception, 'Torrents with the same info_hash, but different announce URLs exist, '
                       'but no more instances are available. Add more instances.',
            lambda: self.choose_shard([])
        )

    def test_simple(self):
        i = self.create_instance()
        self.assertEqual(self.choose_shard([]), i.id)

    def test_locked(self):
        a = self.create_instance()
        b = self.create_instance()
        self.assertEqual(self.choose_shard([a]), b.id)
        self.assertEqual(self.choose_shard([b]), a.id)
        self.assertIn(self.choose_shard([a, b]), [a.id, b.id])
        t = ClientTorrent(announces=self.info.announces, info_hash=self.info.info_hash,
                          instance=a, location=DownloadLocation.objects.get(), size_bytes=0,
                          uploaded_bytes=0, done=1, date_added=timezone.now())
        t.save()
        self.assertRaises(TorrentAlreadyAddedException, lambda: self.choose_shard([]))
        self.assertRaises(TorrentAlreadyAddedException, lambda: self.choose_shard([a]))
        self.assertRaises(TorrentAlreadyAddedException, lambda: self.choose_shard([a, b]))
        t.announces = [['http://boo']]
        t.save()
        for i in range(20):
            self.assertEqual(self.choose_shard([]), b.id)
        self.assertEqual(self.choose_shard([a]), b.id)
        self.assertEqual(self.choose_shard([b]), b.id)
