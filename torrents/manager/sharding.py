from random import choice

from WhatManager3.utils import db_func
from torrents.models import ClientInstance, ClientTorrent


class TorrentAlreadyAddedException(Exception):
    pass


@db_func
def choose_shard(locked_instances, announces_hash, info_hash):
    locked_ids = {i.id for i in locked_instances}
    torrents = list(ClientTorrent.objects.filter(info_hash=info_hash))
    existing = [t for t in torrents if t.announces_hash == announces_hash]
    if len(existing):
        raise TorrentAlreadyAddedException('Torrent already exists in instance {0}'.format(
            existing[0].instance
        ))
    avoid_ids = {t.instance_id for t in torrents}
    instances = ClientInstance.objects.exclude(id__in=avoid_ids).extra(select={
        'torrent_count': 'SELECT COUNT(*) FROM torrents_clienttorrent WHERE '
                         'instance_id = torrents_clientinstance.id'
    }).order_by('-torrent_count').values_list('id', flat=True)
    if not len(instances):
        if len(avoid_ids):
            raise Exception('Torrents with the same info_hash, but different announce URLs exist, '
                            'but no more instances are available. Add more instances.')
        else:
            raise Exception('No instances are available')
    for i in instances:
        if not i in locked_ids:
            return i
    return choice(instances)
