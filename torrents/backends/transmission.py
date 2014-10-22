import asyncio
import base64
from datetime import datetime
import os.path
import ujson

import aiohttp
import pytz

from torrents.backends.base import TorrentClientException, Torrent


class TransmissionException(TorrentClientException):
    pass


class TorrentClient(object):
    def __init__(self, scheme='http', host='localhost', port=9091, path='/transmission/rpc',
                 username=None, password=None):
        self.session_id = ''
        self.url = '{0}://{1}:{2}{3}'.format(scheme, host, port, path)
        if username or password:
            self.auth = (username, password)
        else:
            self.auth = None

    def _call(self, method, **arguments):
        response = yield from aiohttp.request('POST', self.url, auth=self.auth, headers={
            'X-TRANSMISSION-SESSION-ID': self.session_id
        }, data=ujson.dumps({
            'method': method,
            'arguments': arguments,
        }))
        if response.status == 409:
            self.session_id = response.headers['X-TRANSMISSION-SESSION-ID']
            return (yield from self._call(method, **arguments))
        body = yield from response.text()
        if response.status != 200:
            raise TransmissionException(
                'Transmission returned {0}: {1}'.format(response.status, body))
        data = ujson.loads(body)
        if data['result'] != 'success':
            raise TransmissionException(data['result'])
        return data['arguments']

    @asyncio.coroutine
    def get_torrents(self, hashes=None):
        args = {
            'fields': ['name', 'hashString', 'totalSize', 'uploadedEver', 'percentDone',
                       'addedDate', 'error', 'errorString', 'downloadDir', 'trackers'],
        }
        if hashes is not None:
            args['ids'] = hashes
        data = yield from self._call('torrent-get', **args)
        torrents = []
        for item in data['torrents']:
            announces = []
            for tracker in item['trackers']:
                if tracker['tier'] >= len(announces):
                    announces.append([])
                announces[tracker['tier']].append(tracker['announce'])
            torrents.append(Torrent(
                item['hashString'].upper(),
                os.path.dirname(item['downloadDir']),
                item['name'],
                item['totalSize'],
                item['uploadedEver'],
                item['percentDone'],
                datetime.fromtimestamp(item['addedDate'], tz=pytz.UTC),
                item['errorString'] if item['error'] else None,
                announces,
            ))
        return torrents

    @asyncio.coroutine
    def add_torrent(self, torrent_data, add_path):
        args = {
            'metainfo': base64.b64encode(torrent_data),
            'path': add_path,
        }
        yield from self._call('torrent-add', **args)

    @asyncio.coroutine
    def delete_torrent(self, info_hash):
        args = {
            'ids': [info_hash],
            'delete-local-data': True,
        }
        yield from self._call('torrent-remove', **args)
