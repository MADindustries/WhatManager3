# Create your views here.
from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from api.management import ApiManager
from torrents.client import TorrentManagerException
from torrents.models import ClientTorrent
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
    info_hash = request.POST.get('info_hash')
    tracker = request.POST.get('tracker')
    torrent_id = request.POST.get('torrent_id')
    client = ApiManager()
    try:
        client.delete_torrent(info_hash, tracker, torrent_id)
    except TrackerManagerException as e:
        return JsonResponse(e.__dict__)
    except TorrentManagerException as e:
        return JsonResponse(e.__dict__)
    return JsonResponse({'success': True})


def torrents_status(request):
    requested = {}
    if 'info_hashes' in request.GET:
        info_hashes = request.GET['info_hashes'].split(',')
        for info_hash in info_hashes:
            requested[info_hash] = info_hash
    if 'tracker' in request.GET and 'ids' in request.GET:
        ids = request.GET['ids'].split(',')
        model = get_tracker_torrent_model(request.GET['tracker'])
        for t in model.objects.filter(id__in=ids).only('id', 'info_hash'):
            requested[t.id] = t.info_hash
    torrents = {
        t.info_hash: t for t in ClientTorrent.objects.filter(info_hash__in=requested.values())
    }
    statuses = {}
    for key, info_hash in requested.items():
        torrent = torrents.get(info_hash)
        if torrent is None:
            statuses[key] = {
                'status': 'missing',
            }
        elif torrent.done < 1:
            statuses[key] = {
                'status': 'downloading',
                'progress': torrent.done,
            }
        else:
            statuses[key] = {
                'status': 'downloaded',
            }
    return JsonResponse(statuses)
