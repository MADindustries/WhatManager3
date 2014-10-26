from importlib import import_module
import os

from django.db import models
from django.utils.functional import cached_property

from WhatManager3.utils import json_loads, json_dumps
from torrents.utils import decode_announces, encode_announces, hash_announces


class TorrentManager(models.Model):
    host = models.CharField(max_length=256)
    port = models.IntegerField()

    def get_primary_download_location(self):
        return DownloadLocation.objects.get(
            manager=self,
            primary=True
        )


class ClientInstance(models.Model):
    manager = models.ForeignKey(TorrentManager)
    backend = models.CharField(max_length=64)
    params_json = models.CharField(max_length=512)

    @property
    def params(self):
        return json_loads(self.params_json)

    @params.setter
    def params(self, value):
        self.params_json = json_dumps(value)

    @cached_property
    def client(self):
        try:
            backend = import_module(self.backend)
        except ImportError:
            raise Exception('Unable to load backend for {0}'.format(self))
        instance = backend.TorrentClient(**self.params)
        return instance

    def __str__(self):
        return 'ClientInstance({0}, {1})'.format(self.backend, self.params_json)


class DownloadLocation(models.Model):
    manager = models.ForeignKey(TorrentManager)
    path = models.CharField(max_length=512)
    primary = models.BooleanField(default=False)
    tracker = models.CharField(max_length=64, null=True)

    def get_disk_space(self):
        # TODO: we shouldn't be asking the FS, but the torrent manager for this
        stat = os.statvfs(self.path)
        return {
            'free': stat.f_bfree * stat.f_frsize,
            'used': (stat.f_blocks - stat.f_bfree) * stat.f_frsize,
            'total': stat.f_blocks * stat.f_frsize
        }

    @classmethod
    def get_for_tracker(cls, tracker_name):
        return list(DownloadLocation.objects.filter(tracker=tracker_name))


class ClientTorrent(models.Model):
    class Meta:
        unique_together = (
            ('announces_hash', 'info_hash'),
            ('instance', 'info_hash'),
        )

    announces_hash = models.CharField(max_length=40, db_index=True)
    info_hash = models.CharField(max_length=40, db_index=True)

    instance = models.ForeignKey(ClientInstance)
    location = models.ForeignKey(DownloadLocation)
    name = models.CharField(max_length=512)
    size_bytes = models.BigIntegerField()
    uploaded_bytes = models.BigIntegerField()
    done = models.FloatField(db_index=True)
    date_added = models.DateTimeField(db_index=True)
    error = models.CharField(max_length=255, null=True, db_index=True)
    announces_enc = models.CharField(max_length=512)

    def __init__(self, *args, **kwargs):
        announce_list = kwargs.pop('announce_list', None)
        super(ClientTorrent, self).__init__(*args, **kwargs)
        if announce_list:
            self.announces = announce_list

    @property
    def announces(self):
        return decode_announces(self.announces_enc)

    @announces.setter
    def announces(self, value):
        self.announces_enc = encode_announces(value)
        self.announces_hash = hash_announces(value)


class QueuedTorrent(models.Model):
    announces_hash = models.CharField(max_length=40, db_index=True)
    info_hash = models.CharField(max_length=40, db_index=True)
    added = models.DateTimeField(auto_now_add=True)
    delay = models.FloatField(db_index=True)
    path = models.CharField(max_length=512)

    @classmethod
    def top(cls):
        head = list(QueuedTorrent.objects.all().order_by('delay', '-added')[:1])
        if len(head):
            return head[0]
        else:
            raise QueuedTorrent.DoesNotExist()
