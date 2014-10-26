from django.http.response import JsonResponse

from trackers.whatcd.models import FreeleechTorrent, TrackerTorrent


def get_freeleech_torrents(request):
    freeleech_torrents = FreeleechTorrent.objects.all()
    torrents = TrackerTorrent.objects.in_bulk([t.torrent_id for t in freeleech_torrents])
    result = {
        'torrents': []
    }
    for t in freeleech_torrents:
        data = {
            'id': t.torrent_id
        }
        if t.torrent_id in torrents:
            data['info_hash'] = torrents[t.torrent_id].info_hash
            data['announces_hash'] = torrents[t.torrent_id].announces_hash
        result['torrents'].append(data)
    return JsonResponse(result)
