from WhatManager3.settings import DEBUG


class Torrent(object):
    def __init__(self, info_hash, path, name, size_bytes, uploaded_bytes, done, date_added, error,
                 announces):
        """
        Creates a new Torrent instance
        :param info_hash:  SHA1 hash, upper case
        :param name: Name of the torrent
        :param size_bytes: Size of torrent in bytes
        :param uploaded_bytes: How much the client has uploaded on this torrent
        :param done: Float between 0 and 1 - how much has been downloaded
        :param date_added: a datetime object representing when the torrent was added
        :param error: None if there is no error, a string describing it if there is
        :param announces: a list of lists of strings - the announce urls for the trackers (tiered)
        :return: a new Torrent instance
        """
        self.info_hash = info_hash
        self.path = path
        self.name = name
        self.size_bytes = size_bytes
        self.uploaded_bytes = uploaded_bytes
        self.done = done
        self.date_added = date_added
        self.error = error
        self.announces = announces
        if DEBUG:
            assert type(announces) is list
            if len(announces):
                assert type(announces[0]) is list
                assert len(announces[0])
                assert len(announces[0][0])


class TorrentClientException(Exception):
    pass
