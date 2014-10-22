import asyncio
import os
import shutil
from unittest import TestCase
import os.path
import time

from WhatManager3.settings import STORE_PATH
from torrents.utils import TorrentInfo
from trackers.rate_limiter import RateLimiter
from trackers.store import TorrentStore
from trackers.whatcd.tests import music_torrent_data


class TorrentStoreTestCase(TestCase):
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

    def test_put_get_delete(self):
        data = music_torrent_data
        info = TorrentInfo.from_binary(data)
        torrent_path = os.path.join(
            STORE_PATH, 'torrent', info.announces_hash, info.info_hash[:2],
            info.info_hash + '.torrent')
        store = TorrentStore.create()
        self.assertFalse(os.path.exists(torrent_path))
        store.put(data)
        self.assertTrue(os.path.exists(torrent_path))
        self.assertEqual(store.get(info.announces_hash, info.info_hash), data)
        store.delete(info.announces_hash, info.info_hash)
        self.assertFalse(os.path.exists(torrent_path))
        self.assertRaises(OSError, lambda: store.get(info.announces_hash, info.info_hash))


class RateLimiterTestCase(TestCase):
    @asyncio.coroutine
    def _test_rate_limiter_coro(self):
        p = 1
        limiter = RateLimiter(3, 2)
        start = time.time()
        yield from limiter.wait_operation()  # op 1 @ 0
        self.assertAlmostEqual(start, start, p)
        yield from limiter.wait_operation()  # op 2 @ 0
        self.assertAlmostEqual(time.time(), start, p)
        yield from asyncio.sleep(1)
        self.assertAlmostEqual(time.time(), start + 1, p)
        yield from limiter.wait_operation()  # op 3 @ 1
        self.assertAlmostEqual(time.time(), start + 1, p)
        yield from asyncio.sleep(0.5)
        self.assertAlmostEqual(time.time(), start + 1.5, p)
        yield from limiter.wait_operation()  # op 4 @ 1.5 -> 2
        self.assertAlmostEqual(time.time(), start + 2, p)
        yield from limiter.wait_operation()  # op 5 @ 2 -> 2
        self.assertAlmostEqual(time.time(), start + 2, p)
        yield from limiter.wait_operation()  # op 6 @ 2 -> 3
        self.assertAlmostEqual(time.time(), start + 3, p)
        yield from limiter.wait_operation()  # op 7 @ 3 -> 4
        self.assertAlmostEqual(time.time(), start + 4, p)
        yield from limiter.wait_operation()  # op 8 @ 4 -> 4
        self.assertAlmostEqual(time.time(), start + 4, p)

    def test_rate_limter(self):
        asyncio.get_event_loop().run_until_complete(self._test_rate_limiter_coro())
