from torrents.models import ClientTorrent


class SyncException(Exception):
    pass


keys = ['info_hash', 'name', 'size_bytes', 'uploaded_bytes', 'done', 'date_added', 'error']


def compare_dict_torrent(download_locations, values, torrent):
    for key in keys:
        if values[key] != torrent.__dict__[key]:
            return False
    if download_locations[values['location_id']].path != torrent.path:
        return False
    return True


def client_torrent_from_torrent(download_locations, instance, torrent):
    location_id = download_locations.get(torrent.path)
    if location_id is None:
        raise SyncException('Torrent "{0}" in instance {1} is missing DownloadLocation in '
                            'database {2}'.format(torrent.name, instance, torrent.path))
    return ClientTorrent(
        instance=instance,
        location_id=download_locations[torrent.path].id,
        **{key: torrent.__dict__[key] for key in keys}
    )
