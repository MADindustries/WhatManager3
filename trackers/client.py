import requests
from requests.exceptions import ConnectionError

from WhatManager3.settings import TRACKER_MANAGER_HOST, TRACKER_MANAGER_PORT


class TrackerManagerException(Exception):
    def __init__(self, error_code, error, traceback=None):
        self.success = False
        self.error_code = error_code
        self.error = error
        self.traceback = traceback
        super(TrackerManagerException, self).__init__(self, error)

    def __str__(self):
        return 'TrackerManagerException({0}, {1})'.format(self.error_code, self.error)


class TrackerManagerClient(object):
    def add_torrent(self, tracker, torrent_id, **kwargs):
        url = 'http://{0}:{1}/torrents/add'.format(TRACKER_MANAGER_HOST, TRACKER_MANAGER_PORT)
        try:
            data = {
                'tracker': tracker,
                'id': torrent_id
            }
            data.update(kwargs)
            response = requests.post(url, data=data)
        except ConnectionError:
            raise TrackerManagerException(
                'tracker_manager_error',
                'Your tracker manager is not running on {0}:{1}'.format(
                    self.torrent_manager.host, self.torrent_manager.port))
        try:
            response_json = response.json()
        except ValueError:
            raise TrackerManagerException(
                'tracker_manager_error',
                'Invalid JSON response: {0}'.format(response.text)
            )
        if not response_json['success']:
            raise TrackerManagerException(
                response_json.get('error_code'),
                response_json.get('error'),
                response_json.get('traceback')
            )
