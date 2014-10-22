from django.db import models

from torrents.utils import encode_announces, decode_announces, hash_announces


class TrackerTorrentBase(models.Model):
    class Meta(object):
        abstract = True
        index_together = (('info_hash', 'announces_hash'),)

    id = models.IntegerField(primary_key=True)
    info_hash = models.CharField(max_length=40, db_index=True)
    announces_hash = models.CharField(max_length=40, db_index=True)
    announces_enc = models.CharField(max_length=512)
    retrieved = models.DateTimeField(db_index=True)

    def __init__(self, *args, **kwargs):
        announces = kwargs.pop('announces', None)
        super(TrackerTorrentBase, self).__init__(*args, **kwargs)
        if announces:
            self.announces = announces

    @property
    def announces(self):
        return decode_announces(self.announces_enc)

    @announces.setter
    def announces(self, value):
        self.announces_enc = encode_announces(value)
        self.announces_hash = hash_announces(value)
