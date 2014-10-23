# Create your views here.
from functools import reduce

from django.db.models.aggregates import Sum
from django.db.models import Q
from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from api.management import ApiManager
from torrents.client import TorrentManagerException
from torrents.models import ClientTorrent, DownloadLocation
from trackers.client import TrackerManagerException
from trackers.loader import get_tracker_torrent_model


@csrf_exempt
@require_POST
def add_torrent(request):
    tracker = request.POST['tracker']
    torrent_id = request.POST['torrent_id']
    client = ApiManager()
    try:
        client.add_torrent(tracker, torrent_id)
    except TrackerManagerException as e:
        return JsonResponse(e.__dict__)
    except TorrentManagerException as e:
        return JsonResponse(e.__dict__)
    return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def delete_torrent(request):
    torrent_id = request.POST.get('torrent_id')
    client = ApiManager()
    try:
        client.delete_torrent(torrent_id)
    except TrackerManagerException as e:
        return JsonResponse(e.__dict__)
    except TorrentManagerException as e:
        return JsonResponse(e.__dict__)
    return JsonResponse({'success': True})


def torrents_status(request):
    qs = []
    requested = {}
    if 'tracker' in request.GET and 'ids' in request.GET:
        ids = request.GET['ids'].split(',')
        model = get_tracker_torrent_model(request.GET['tracker'])
        for t in model.objects.filter(id__in=ids).only('id', 'announces_hash', 'info_hash'):
            requested[t.id] = (t.announces_hash, t.info_hash)
            qs.append(Q(announces_hash=t.announces_hash, info_hash=t.info_hash))
    torrents = {
        (t.announces_hash, t.info_hash): t for t in
        ClientTorrent.objects.filter(reduce(lambda a, b: a | b), qs)
    }
    statuses = {}
    for torrent_id, key in requested.items():
        torrent = torrents.get(key)
        if torrent is None:
            statuses[torrent_id] = {'status': 'missing'}
        elif torrent.done < 1:
            statuses[torrent_id] = {'status': 'downloading', 'progress': torrent.done, }
        else:
            statuses[torrent_id] = {'status': 'downloaded'}
    return JsonResponse(statuses)


def site_stats(request):
    torrent_count = ClientTorrent.objects.count()
    total_size = ClientTorrent.objects.all().aggregate(Sum('size_bytes'))['size_bytes__sum'] or 0
    buffer = 0
    locations = []
    for location in DownloadLocation.objects.all():
        space = location.get_disk_space()
        space['path'] = location.path
        space['torrents'] = ClientTorrent.objects.filter(location=location).count()
        locations.append(space)
    return JsonResponse({
        'torrents': torrent_count,
        'torrentsSize': total_size,
        'buffer': buffer,
        'downloadLocations': locations,
    })
