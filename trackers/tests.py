import asyncio
import os
import shutil
from unittest import TestCase, mock
import os.path
import time

from WhatManager3.settings import STORE_PATH
from torrents.utils import TorrentInfo
from trackers import rate_limiter
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
    def _test_rate_limiter_coro(self, mock_sleep, mock_time):
        def _sleep(t):
            # advance time when sleep is called
            mock_time.return_value += t
            yield

        mock_time.return_value = 0
        mock_sleep.side_effect = _sleep
        limiter = rate_limiter.RateLimiter(3, 2)

        yield from limiter.wait_operation()  # op 1 @ 0
        yield from limiter.wait_operation()  # op 2 @ 0
        yield from _sleep(1)
        yield from limiter.wait_operation()  # op 3 @ 1
        self.assertEqual(0, mock_sleep.call_count)
        mock_sleep.reset_mock()

        yield from _sleep(0.5)
        yield from limiter.wait_operation()  # op 4 @ 1.5 -> 2
        mock_sleep.assert_called_once_with(0.5)
        self.assertEqual(1, mock_sleep.call_count)
        mock_sleep.reset_mock()

        yield from limiter.wait_operation()  # op 5 @ 2 -> 2
        yield from limiter.wait_operation()  # op 6 @ 2 -> 3
        mock_sleep.assert_called_once_with(1.0)
        self.assertEqual(1, mock_sleep.call_count)
        mock_sleep.reset_mock()

        yield from limiter.wait_operation()  # op 7 @ 3 -> 4
        mock_sleep.assert_called_once_with(1.0)
        self.assertEqual(1, mock_sleep.call_count)
        mock_sleep.reset_mock()

        yield from limiter.wait_operation()  # op 8 @ 4 -> 4
        self.assertEqual(0, mock_sleep.call_count)

    @mock.patch.object(time, 'time')
    @mock.patch.object(asyncio, 'sleep')
    def test_rate_limter(self, mock_sleep, mock_time):
        asyncio.get_event_loop().run_until_complete(
            self._test_rate_limiter_coro(mock_sleep, mock_time))
