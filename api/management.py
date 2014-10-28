import os.path

from torrents.client import TorrentManagerClient
from torrents.models import DownloadLocation
from trackers.client import TrackerManagerClient, TrackerManagerException
from trackers.loader import get_tracker_torrent_model
from trackers.store import TorrentStore


class ApiManager(object):
    def __init__(self):
        self.tracker_manager = TrackerManagerClient()
        self.torrent_manager = TorrentManagerClient()

    def add_torrent(self, tracker, torrent_id, tracker_manager_args={}):
        self.tracker_manager.add_torrent(tracker, torrent_id, **tracker_manager_args)
        tracker_torrent = get_tracker_torrent_model(tracker).objects.get(id=torrent_id)
        torrent_data = TorrentStore.create().get(
            tracker_torrent.announces_hash, tracker_torrent.info_hash)
        locations = [i for i in DownloadLocation.get_for_tracker(tracker) if i.primary]
        if len(locations) != 1:
            raise TrackerManagerException(
                None, 'You must have exactly one primary download location for {0}'.format(
                    tracker))
        destination = os.path.join(locations[0].path, str(tracker_torrent.id))
        self.torrent_manager.add_torrent(torrent_data, destination)

    def delete_torrent(self, torrent_id=None):
        self.torrent_manager.delete_torrent(torrent_id)
