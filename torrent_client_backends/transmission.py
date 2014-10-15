import asyncio
from datetime import datetime

import aiohttp
import pytz

import ujson
import os.path
from torrent_client_backends.base import TorrentClientException, Torrent


class TransmissionException(TorrentClientException):
    pass


class TorrentClient(object):
    def __init__(self, url, auth=None):
        self.session_id = ''
        self.url = url
        self.auth = auth

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
        data = ujson.loads(body)
        if data['result'] != 'success':
            raise TransmissionException(data['result'])
        return data['arguments']

    def get_torrents(self, hashes=None):
        args = {
            'fields': [ 'name', 'hashString', 'totalSize', 'uploadedEver', 'percentDone',
                        'addedDate', 'error', 'errorString', 'downloadDir'],
        }
        if hashes is not None:
            args['ids'] = hashes
        data = yield from self._call('torrent-get', **args)
        torrents = []
        for item in data['torrents']:
            torrents.append(Torrent(
                item['hashString'].upper(),
                os.path.dirname(item['downloadDir']),
                item['name'],
                item['totalSize'],
                item['uploadedEver'],
                item['percentDone'],
                datetime.fromtimestamp(item['addedDate']),
                item['error'] if item['error'] else None,
            ))
        return torrents
