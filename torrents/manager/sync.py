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


def client_torrent_from_torrent(download_locations, instance, torrent, torrent_id=None):
    location_id = download_locations.get(torrent.path)
    if location_id is None:
        return None
        # raise SyncException('Torrent "{0}" in instance {1} is missing DownloadLocation in '
        # 'database {2}'.format(torrent.name, instance, torrent.path))
    return ClientTorrent(
        id=torrent_id,
        instance=instance,
        location_id=download_locations[torrent.path].id,
        announces=torrent.announces,
        **{key: torrent.__dict__[key] for key in keys}
    )


def compute_sync(instance, download_locations, m_torrents, t_torrents):
    download_locations_id = {d.id: d for d in download_locations}
    download_locations_path = {d.path: d for d in download_locations}
    new_torrents = []
    changed_torrents = []
    deleted_hashes = []

    for info_hash, t_torrent in t_torrents.items():
        m_torrent = m_torrents.get(info_hash)
        if m_torrent is None:
            client_torrent = client_torrent_from_torrent(
                download_locations_path, instance, t_torrent)
            if client_torrent is not None:
                new_torrents.append(client_torrent)
        elif not compare_dict_torrent(download_locations_id, m_torrent, t_torrent):
            client_torrent = client_torrent_from_torrent(
                download_locations_path, instance, t_torrent, torrent_id=m_torrent['id'])
            if client_torrent is not None:
                changed_torrents.append(client_torrent)
    for info_hash in m_torrents:
        if not info_hash in t_torrents:
            deleted_hashes.append(info_hash)
    return new_torrents, changed_torrents, deleted_hashes
