import os.path

from WhatManager3.utils import html_unescape


WHAT_RELEASE_TYPES = (
    (1, 'Album'),
    (3, 'Soundtrack'),
    (5, 'EP'),
    (6, 'Anthology'),
    (7, 'Compilation'),
    (8, 'DJ Mix'),
    (9, 'Single'),
    (11, 'Live album'),
    (13, 'Remix'),
    (14, 'Bootleg'),
    (15, 'Interview'),
    (16, 'Mixtape'),
    (21, 'Unknown'),
    (22, 'Concert Recording'),
    (23, 'Demo'),
)

IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif', '.tif']


def get_release_type_name(id):
    id = int(id)
    for release_type in WHAT_RELEASE_TYPES:
        if release_type[0] == id:
            return release_type[1]
    return None


def get_release_type_id(name):
    name = str(name)
    for release_type in WHAT_RELEASE_TYPES:
        if release_type[1] == name:
            return release_type[0]
    return None


def parse_file(file):
    parts = file.replace('}}}', '').split('{{{')
    return {
        'name': html_unescape(parts[0]),
        'size': int(parts[1])
    }


def is_image_file(file):
    ext = os.path.splitext(file)[1]
    return any(e == ext for e in IMAGE_EXTS)


def parse_file_list(file_list):
    files = file_list.split('|||')
    return sorted([parse_file(f) for f in files], key=lambda i: i['name'])


class JoinedArtistsBuilder(object):
    def __init__(self, joined_artists_builder=None):
        if joined_artists_builder is None:
            self.result = []
        else:
            self.result = list(joined_artists_builder.result)

    def append_joined(self, join_string, artists):
        for a in artists:
            self.result.append({
                u'id': a['id'],
                u'name': a['name'],
                u'join': join_string,
            })
        self.result[-1]['join'] = ''

    def append_artist(self, artist):
        self.result.append({
            u'id': artist['id'],
            u'name': html_unescape(artist['name']),
            u'join': '',
        })

    def append_join(self, join_string):
        assert not self.result[-1][u'join'], 'Last join should be empty before adding a new join'
        self.result[-1][u'join'] = join_string

    def clear(self):
        self.result = []


def get_artists_list(music_info):
    a_main = music_info['artists']
    a_composers = music_info['composers']
    a_conductors = music_info['conductor']
    a_djs = music_info['dj']

    if len(a_main) == 0 and len(a_conductors) == 0 and len(a_djs) == 0 and len(a_composers) == 0:
        return []

    builder = JoinedArtistsBuilder()

    if len(a_composers) and len(a_composers) < 3:
        builder.append_joined(u' & ', a_composers)
        if len(a_composers) < 3 and len(a_main) > 0:
            builder.append_join(u' performed by ')

    composer_builder = JoinedArtistsBuilder(builder)

    if len(a_main):
        if len(a_main) <= 2:
            builder.append_joined(u' & ', a_main)
        else:
            builder.append_artist({u'id': -1, u'name': u'Various Artists'})

    if len(a_conductors):
        if (len(a_main) or len(a_composers)) and (len(a_composers) < 3 or len(a_main)):
            builder.append_join(u' under ')
        if len(a_conductors) <= 2:
            builder.append_joined(u' & ', a_conductors)
        else:
            builder.append_artist({u'id': -1, u'name': u'Various Conductors'})

    if len(a_composers) and len(a_main) + len(a_conductors) > 3 and len(a_main) > 1 and len(
            a_conductors) > 1:
        builder = composer_builder
        builder.append_artist({u'id': -1, u'name': u'Various Artists'})
    elif len(a_composers) > 2 and len(a_main) + len(a_conductors) == 0:
        builder.clear()
        builder.append_artist({u'id': -1, u'name': u'Various Composers'})

    if len(a_djs):
        if len(a_djs) <= 2:
            builder.clear()
            builder.append_joined(u' & ', a_djs)
        else:
            builder.clear()
            builder.append_artist({u'id': -1, u'name': u'Various DJs'})

    return builder.result


def get_artists(music_info):
    artists_list = get_artists_list(music_info)
    result = []
    for a in artists_list:
        result.append(a['name'])
        result.append(a['join'])
    return u''.join(result)

