import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
import logging

from django.db import transaction
from django.db.utils import IntegrityError
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.web import Application, url, RequestHandler

from WhatManager3.asyncio_helper import JsonWhatManagerRequestHandler
from WhatManager3.utils import db_func, prune_connections
from torrents.manager.sync import compute_sync
from torrents.manager.utils import Timer
from torrents.models import ClientInstance, ClientTorrent, DownloadLocation, TorrentManager, \
    QueuedTorrent
from torrents.manager.sharding import choose_shard, TorrentAlreadyAddedException
from torrents.utils import TorrentInfo
from trackers.store import TorrentStore


logging.basicConfig(level=logging.INFO)


class ClientManager(object):
    UPDATE_INTERVAL = 3
    FULL_UPDATE_INTERVAL = 30
    SIMULTANEOUS_ADDS = 2
    QUEUE_POP_INTERVAL = 5

    @db_func
    def __init__(self, event_loop=None):
        self.logger = logging.getLogger('torrent_manager.client_updater')
        self.loop = event_loop or asyncio.get_event_loop()
        self.instances = {
            i.id: i for i in ClientInstance.objects.all()
        }
        for instance in self.instances.values():
            instance.lock = asyncio.Lock(loop=self.loop)
        self.update_pool = ThreadPoolExecutor(1)
        self.pool = ThreadPoolExecutor(2)
        self.update_index = 0
        self.info_hashes = set()
        self.torrent_store = TorrentStore.create()

    def start(self):
        asyncio.async(self.full_update_loop(), loop=self.loop)
        for instance in self.instances.values():
            asyncio.async(self.update_loop(instance), loop=self.loop)
        asyncio.async(self.queue_loop(), loop=self.loop)

    @asyncio.coroutine
    @db_func
    def queue_pop(self):
        try:
            top = QueuedTorrent.top()
        except QueuedTorrent.DoesNotExist:
            return
        torrent_data = self.torrent_store.get(top.announces_hash, top.info_hash)
        yield from self.add_torrent(torrent_data, DownloadLocation.objects.get().path)
        prune_connections()
        top.delete()

    @asyncio.coroutine
    def queue_loop(self):
        try:
            yield from self.queue_pop()
        finally:
            self.loop.call_later(self.QUEUE_POP_INTERVAL, asyncio.async, self.queue_loop())

    @db_func
    def get_torrents(self, query):
        with Timer(self.logger, 'Pull torrents from DB') as t:
            torrents = {
                t['info_hash']: t for t in query
            }
            download_locations = list(DownloadLocation.objects.all())
            t.op += ' fetched {0}'.format(len(torrents))
            return torrents, download_locations

    @db_func
    def update_db(self, new_torrents, changed_torrents, deleted_hashes):
        try:
            with transaction.atomic():
                ClientTorrent.objects.bulk_create(new_torrents)
        except IntegrityError as e:
            self.logger.error('bulk_create failed with {0}. Trying one by one...'.format(e))
            for new_torrent in new_torrents:
                try:
                    with transaction.atomic():
                        new_torrent.save()
                except IntegrityError as e:
                    self.logger.error(
                        'Saving torrent failed. announces_hash={0} info_hash={1} '
                        'announces={2} name={3}'.format(
                            new_torrent.announces_hash, new_torrent.info_hash,
                            new_torrent.announces,
                            new_torrent.name
                        ))
                    raise
        with transaction.atomic():
            for torrent in changed_torrents:
                torrent.save()
        with transaction.atomic():
            ClientTorrent.objects.filter(info_hash__in=deleted_hashes).delete()

    @asyncio.coroutine
    def apply_sync(self, pool, instance, download_locations, m_torrents, t_torrents):
        change_set = compute_sync(instance, download_locations, m_torrents, t_torrents)
        self.logger.info('{0} sync is {1} new, {2} changed, {3} deleted'.format(
            instance, len(change_set[0]), len(change_set[1]), len(change_set[2])
        ))
        yield from self.loop.run_in_executor(pool, self.update_db, *change_set)

    @asyncio.coroutine
    def update(self, instance):
        with Timer(self.logger, 'Full update {0}'.format(instance)):
            query = ClientTorrent.objects.filter(instance=instance).values()
            m_task = self.loop.run_in_executor(self.update_pool, self.get_torrents, query)
            with Timer(self.logger, 'Pull torrents from Transmission'):
                t_torrents = {
                    t.info_hash: t for t in
                    (yield from instance.client.get_torrents())
                }
            m_torrents, download_locations = yield from m_task
            yield from self.apply_sync(self.update_pool, instance, download_locations,
                                       m_torrents, t_torrents)

    @asyncio.coroutine
    def update_partial(self, instance):
        with Timer(self.logger, 'Partial update {0}'.format(instance)):
            query = ClientTorrent.objects.filter(instance=instance, done__lt=1).values()
            m_torrents, download_locations = yield from self.loop.run_in_executor(
                self.update_pool, self.get_torrents, query)
            t_torrents = {
                t.info_hash: t for t in
                (yield from instance.client.get_torrents(list(m_torrents)))
            }
            yield from self.apply_sync(self.update_pool, instance, download_locations,
                                       m_torrents, t_torrents)

    @asyncio.coroutine
    def update_loop(self, instance):
        try:
            with (yield from instance.lock):
                yield from self.update_partial(instance)
        except Exception:
            raise
        finally:
            self.loop.call_later(self.UPDATE_INTERVAL, asyncio.async, self.update_loop(instance))

    @asyncio.coroutine
    def full_update_loop(self):
        for instance in self.instances.values():
            try:
                with (yield from instance.lock):
                    yield from self.update(instance)
            except Exception:
                raise
        self.loop.call_later(self.FULL_UPDATE_INTERVAL, asyncio.async, self.full_update_loop())

    @asyncio.coroutine
    def update_added_torrent(self, instance, info_hash):
        with Timer(self.logger, 'Update added torrent {0}'.format(info_hash)):
            query = ClientTorrent.objects.filter(instance=instance, info_hash=info_hash)
            m_torrents, download_locations = yield from self.loop.run_in_executor(
                self.pool, self.get_torrents, query)
            t_torrents = {
                t.info_hash: t for t in
                (yield from instance.client.get_torrents([info_hash]))
            }
            yield from self.apply_sync(self.pool, instance, download_locations,
                                       m_torrents, t_torrents)

    @asyncio.coroutine
    def add_torrent(self, torrent_data, add_path):
        info = TorrentInfo.from_binary(torrent_data)
        hashes_key = (info.announces_hash, info.info_hash)
        if hashes_key in self.info_hashes:
            raise TorrentAlreadyAddedException()
        self.info_hashes.add(hashes_key)
        try:
            locked_instances = [i for i in self.instances if not i.lock.locked()]
            shard = yield from self.loop.run_in_executor(
                self.pool, choose_shard, locked_instances, info)
            instance = self.instances[shard.id]
            with (yield from instance.lock):
                yield from instance.client.add_torrent(torrent_data, add_path)
                yield from self.update_added_torrent(instance, info.info_hash)
        finally:
            self.info_hashes.remove(hashes_key)

    @asyncio.coroutine
    @db_func
    def delete_torrent(self, torrent_id):
        not_found_resp = {
            'success': False,
            'error_code': 'torrent_not_found',
            'error': 'Torrent was not found',
        }
        try:
            torrent = ClientTorrent.objects.get(id=torrent_id)
        except ClientTorrent.DoesNotExist:
            return not_found_resp
        instance = self.instances[torrent.instance_id]
        with (yield from instance.lock):
            try:
                ClientTorrent.objects.get(id=torrent_id)
            except ClientTorrent.DoesNotExist:
                return not_found_resp
            yield from instance.client.delete_torrent(torrent.info_hash)
            prune_connections()
            torrent.delete()
            return {
                'success': True
            }


class AddTorrentHandler(JsonWhatManagerRequestHandler):
    def __init__(self, *args, **kwargs):
        self.updater = kwargs.pop('updater')
        super(AddTorrentHandler, self).__init__(*args, **kwargs)

    @asyncio.coroutine
    def post_json(self):
        add_path = self.get_body_argument('path', None)
        if 'torrent' not in self.request.files:
            return {
                'success': False,
                'error_code': 'missing_parameter',
                'error': 'Please supply a torrent file',
            }
        elif add_path is None:
            return {
                'success': False,
                'error_code': 'missing_parameter',
                'error': 'Please supply a path parameter',
            }
        torrent_data = self.request.files['torrent'][0].body
        try:
            yield from self.updater.add_torrent(torrent_data, add_path)
            return {
                'success': True
            }
        except TorrentAlreadyAddedException:
            return {
                'success': False,
                'error_code': 'torrent_already_added',
                'error': 'Torrent has already been added.',
            }


class DeleteTorrentHandler(JsonWhatManagerRequestHandler):
    def __init__(self, *args, **kwargs):
        self.updater = kwargs.pop('updater')
        super(DeleteTorrentHandler, self).__init__(*args, **kwargs)

    @asyncio.coroutine
    def post_json(self):
        torrent_id = self.get_body_argument('torrent_id', None)
        if torrent_id:
            return (yield from self.updater.delete_torrent(torrent_id))
        else:
            return {
                'success': False,
                'error_code': 'missing_parameter',
                'error': 'Please either info_hash or tracker and torrent_id',
            }


class PingHandler(RequestHandler):
    def get(self):
        self.write('OK')


@db_func
def get_torrent_manager():
    return TorrentManager.objects.get()


def run():
    AsyncIOMainLoop().install()
    loop = asyncio.get_event_loop()
    updater = ClientManager(loop)
    app = Application([
        url('/torrents/add', AddTorrentHandler, kwargs={'updater': updater}),
        url('/torrents/delete', DeleteTorrentHandler, kwargs={'updater': updater}),
        url('/ping', PingHandler),
    ])
    torrent_manager = get_torrent_manager()
    app.listen(torrent_manager.port)
    updater.start()
    loop.run_forever()
