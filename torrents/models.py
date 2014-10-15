from importlib import import_module

from django.db import models
from django.utils.functional import cached_property

import ujson


class ClientInstance(models.Model):
    backend = models.CharField(max_length=64)
    params_json = models.CharField(max_length=512)

    @property
    def params(self):
        return ujson.loads(self.params_json)

    @params.setter
    def set_params(self, value):
        self.params_json = ujson.dumps(value)

    @cached_property
    def client(self):
        backend = import_module(self.backend)
        instance = backend.TorrentClient(**self.params)
        return instance


class DownloadLocation(models.Model):
    path = models.CharField(max_length=512)


class ClientTorrent(models.Model):
    info_hash = models.CharField(max_length=40, primary_key=True)

    instance = models.ForeignKey(ClientInstance)
    location = models.ForeignKey(DownloadLocation)
    name = models.CharField(max_length=1024)
    size_bytes = models.BigIntegerField()
    uploaded_bytes = models.BigIntegerField()
    done = models.FloatField()
    date_added = models.DateTimeField()
    error = models.IntegerField(null=True)
