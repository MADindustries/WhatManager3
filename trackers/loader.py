from trackers.whatcd.client import TrackerClient as WhatTrackerClient


client_types = {
    WhatTrackerClient.name: WhatTrackerClient
}


def get_clients():
    return {
        k: v() for k, v in client_types.items()
    }


def get_tracker_torrent_model(tracker):
    return client_types[tracker].tracker_torrent_model
