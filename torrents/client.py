import requests
from requests.exceptions import ConnectionError

from torrents.models import TorrentManager


class TorrentManagerException(Exception):
    def __init__(self, error_code, error, traceback=None):
        self.success = False
        self.error_code = error_code
        self.error = error
        self.traceback = traceback
        super(TorrentManagerException, self).__init__(self, error)

    def __str__(self):
        return 'TorrentManagerException({0}, {1})'.format(self.error_code, self.error)


def handle_errors(f):
    def inner(self, *args, **kwargs):
        try:
            response = f(self, *args, **kwargs)
        except ConnectionError:
            raise TorrentManagerException(
                'torrent_manager_error',
                'Your tracker manager is not connectible on {0}:{1}'.format(
                    self.torrent_manager.host, self.torrent_manager.port
                ))
        try:
            response_json = response.json()
        except ValueError:
            raise TorrentManagerException(
                'torrent_manager_error',
                'Invalid JSON response: {0}'.format(response.text)
            )
        if not response_json['success']:
            raise TorrentManagerException(
                response_json.get('error_code'),
                response_json.get('error'),
                response_json.get('traceback')
            )

    return inner


class TorrentManagerClient(object):
    def __init__(self):
        self.torrent_manager = TorrentManager.objects.get()

    @handle_errors
    def add_torrent(self, torrent_data, add_path, **kwargs):
        url = 'http://{0}:{1}/torrents/add'.format(self.torrent_manager.host,
                                                   self.torrent_manager.port)
        files = {
            'torrent': torrent_data
        }
        data = {
            'path': add_path,
        }
        data.update(kwargs)
        return requests.post(url, data=data, files=files)

    @handle_errors
    def delete_torrent(self, info_hash=None, tracker=None, torrent_id=None):
        """
        Deletes a torrent. Pass either info_hash or tracker and torrent_id
        """
        url = 'http://{0}:{1}/torrents/delete'.format(self.torrent_manager.host,
                                                      self.torrent_manager.port)
        assert info_hash or (tracker and torrent_id)
        if info_hash:
            data = {
                'info_hash': info_hash
            }
        else:
            data = {
                'tracker': tracker,
                'torrent_id': torrent_id
            }
        return requests.post(url, data=data)
