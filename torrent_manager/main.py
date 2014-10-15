import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
import time

from django.db import close_old_connections, transaction
from tornado.web import RequestHandler

from torrent_manager.sync import client_torrent_from_torrent, compare_dict_torrent

from torrents.models import ClientInstance, ClientTorrent, DownloadLocation


def db_func(func):
    def inner(*args, **kwargs):
        close_old_connections()
        return func(*args, **kwargs)

    return inner


class ClientUpdater(object):
    UPDATE_INTERVAL = 2

    def __init__(self, event_loop=None):
        self.instances = list(ClientInstance.objects.all())
        self.event_loop = event_loop or asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(len(self.instances) * 100)

    def start(self):
        for instance in self.instances:
            asyncio.async(self.update_loop(instance), loop=self.event_loop)

    @db_func
    def get_torrents(self, instance):
        print('get_torrents', time.time())
        torrents = {
            t['info_hash']: t for t in
            ClientTorrent.objects.filter(instance=instance).values()
        }
        download_locations = list(DownloadLocation.objects.all())
        return torrents, download_locations

    @db_func
    def update_db(self, new_torrents, changed_torrents, deleted_hashes):
        with transaction.atomic():
            ClientTorrent.objects.bulk_create(new_torrents)
        with transaction.atomic():
            for torrent in changed_torrents:
                torrent.save()
        with transaction.atomic():
            ClientTorrent.objects.filter(info_hash__in=deleted_hashes).delete()
        print(new_torrents)
        print(changed_torrents)
        print(deleted_hashes)

    @asyncio.coroutine
    def update(self, instance):
        m_task = self.event_loop.run_in_executor(self.executor, self.get_torrents, instance)
        t_torrents = {
            t.info_hash: t for t in
            (yield from instance.client.get_torrents())
        }
        m_torrents, download_locations = yield from m_task
        download_locations_id = {d.id: d for d in download_locations}
        download_locations_path = {d.path: d for d in download_locations}
        new_torrents = []
        changed_torrents = []
        for hash, t_torrent in t_torrents.items():
            m_torrent = m_torrents.get(hash)
            if m_torrent is None:
                new_torrents.append(client_torrent_from_torrent(
                    download_locations_path, instance, t_torrent))
            elif not compare_dict_torrent(download_locations_id, m_torrent, t_torrent):
                changed_torrents.append(client_torrent_from_torrent(
                    download_locations_path, instance, t_torrent))
        deleted_hashes = []
        for hash in m_torrents:
            if not hash in t_torrents:
                deleted_hashes.append(hash)

        self.event_loop.run_in_executor(
            self.executor, self.update_db, new_torrents, changed_torrents, deleted_hashes)

    @asyncio.coroutine
    def update_loop(self, instance):
        try:
            yield from self.update(instance)
        except Exception:
            raise
        finally:
            self.event_loop.call_later(self.UPDATE_INTERVAL, asyncio.async,
                                       self.update_loop(instance))


class MainHandler(RequestHandler):
    def get(self):
        self.write('oh hi')
        print('hi')


def main():
    # AsyncIOMainLoop().install()
    loop = asyncio.get_event_loop()
    updater = ClientUpdater(loop)
    loop.call_soon(updater.start)
    # app = Application([
    # url('/', MainHandler)
    # ])
    # app.listen(8888)
    loop.run_forever()
