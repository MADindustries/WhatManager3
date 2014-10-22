import os
import os.path

from WhatManager3 import settings
from torrents.utils import TorrentInfo


class TorrentStore(object):
    def __init__(self, dir):
        self.dir = dir

    def get_path(self, announces_hash, info_hash):
        assert len(info_hash) == 40
        assert len(announces_hash) == 40
        return os.path.join(self.dir, announces_hash, info_hash[:2], info_hash + '.torrent')

    def get(self, announces_hash, info_hash):
        file_path = self.get_path(announces_hash, info_hash)
        with open(file_path, 'rb') as f:
            return f.read()

    def put(self, content):
        info = TorrentInfo.from_binary(content)
        file_path = self.get_path(info.announces_hash, info.info_hash)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                if f.read() != content:
                    raise Exception('Trying to put a torrent with the same info_hash an announces'
                                    ' but different content')
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        with open(file_path, 'wb') as f:
            f.write(content)

    def delete(self, announces_hash, info_hash):
        file_path = self.get_path(announces_hash, info_hash)
        os.remove(file_path)

    @classmethod
    def create(cls):
        return TorrentStore(os.path.join(settings.STORE_PATH, 'torrent'))
