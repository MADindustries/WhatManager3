import os.path

from torrents.client import TorrentManagerClient
from torrents.models import DownloadLocation
from trackers.client import TrackerManagerClient
from trackers.loader import get_tracker_torrent_model
from trackers.store import TorrentStore


class ApiManager(object):
    def __init__(self):
        self.tracker_manager = TrackerManagerClient()
        self.torrent_manager = TorrentManagerClient()

    def add_torrent(self, tracker, torrent_id, tracker_manager_args={}):
        self.tracker_manager.add_torrent(tracker, torrent_id, **tracker_manager_args)
        tracker_torrent = get_tracker_torrent_model(tracker).objects.get(id=torrent_id)
        torrent_data = TorrentStore.create().get(tracker_torrent.info_hash)
        dl = DownloadLocation.objects.get()
        destination = os.path.join(dl.path, str(tracker_torrent.id))
        self.torrent_manager.add_torrent(torrent_data, destination)

    def delete_torrent(self, info_hash=None, tracker=None, torrent_id=None):
        self.torrent_manager.delete_torrent(info_hash, tracker, torrent_id)
