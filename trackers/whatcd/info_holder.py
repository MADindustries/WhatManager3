from django.utils.functional import cached_property

from trackers.whatcd.meta import get_artists


class WhatTorrentInfo(object):
    def __init__(self, info_dict):
        self.info_dict = info_dict
        self._group = self.info_dict['group']
        self._torrent = self.info_dict['torrent']

    @cached_property
    def id(self):
        return self._torrent['id']

    @cached_property
    def group_id(self):
        return self._group['id']

    @cached_property
    def joined_artists(self):
        return get_artists(self._group['musicInfo'])

    @cached_property
    def category_id(self):
        return self._group['categoryId']

    @cached_property
    def release_type_id(self):
        return self._group['releaseType']

    @cached_property
    def media(self):
        return self._torrent['media']

    @cached_property
    def format(self):
        return self._torrent['format']

    @cached_property
    def encoding(self):
        return self._torrent['encoding']

    @cached_property
    def size(self):
        return self._torrent['size']

    @cached_property
    def user_id(self):
        return self._torrent['userId']
