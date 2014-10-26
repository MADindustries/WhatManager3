from django.db import models, transaction
from django.utils import timezone
from django.utils.functional import cached_property

from WhatManager3.utils import html_unescape, parse_db_datetime, json_dumps, json_loads
from trackers.models import TrackerTorrentBase
from trackers.whatcd.info_holder import WhatTorrentInfo
from trackers.whatcd.meta import get_artists


class Artist(models.Model):
    retrieved = models.DateTimeField(db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    image = models.CharField(max_length=255, null=True)
    wiki_body = models.TextField(null=True)
    vanity_house = models.BooleanField(default=False)
    info_json = models.TextField(null=True)

    @classmethod
    def get_or_create_shell(cls, artist_id, name, retrieved):
        try:
            artist = Artist.objects.get(id=artist_id)
            alias = None
            if artist.name != name:
                alias = ArtistAlias.get_or_create(artist, name)
            return artist, alias
        except Artist.DoesNotExist:
            new_artist = Artist(
                id=artist_id,
                name=name,
                retrieved=retrieved,
            )
            new_artist.save()
            return new_artist, None


class ArtistAlias(models.Model):
    artist = models.ForeignKey(Artist)
    name = models.CharField(max_length=200, unique=True)

    @classmethod
    def get_or_create(cls, artist, name):
        try:
            return artist.artistalias_set.get(name=name)
        except ArtistAlias.DoesNotExist:
            alias = ArtistAlias(
                artist=artist,
                name=name,
            )
            alias.save()
            return alias


class TorrentArtist(models.Model):
    artist = models.ForeignKey(Artist)
    artist_alias = models.ForeignKey(ArtistAlias, null=True)
    torrent_group = models.ForeignKey('TorrentGroup')
    importance = models.IntegerField()


class TorrentGroup(models.Model):
    retrieved = models.DateTimeField()
    artists = models.ManyToManyField(Artist, through=TorrentArtist)
    wiki_body = models.TextField()
    wiki_image = models.CharField(max_length=255)
    joined_artists = models.TextField()
    name = models.CharField(max_length=300)  # Indexed with a RunSQL migration
    year = models.IntegerField()
    record_label = models.CharField(max_length=80)
    catalogue_number = models.CharField(max_length=80)
    release_type = models.IntegerField()
    category_id = models.IntegerField()
    category_name = models.CharField(max_length=32)
    time = models.DateTimeField()
    vanity_house = models.BooleanField(default=False)
    info_json = models.TextField()
    # Will contain the JSON for the "torrent" response field if this was fetched through
    # action=torrentgroup. If it was created from an action=torrent, then it will be NULL
    torrents_json = models.TextField(null=True)

    def add_artists(self, importance, artists):
        for artist in artists:
            what_artist, artist_alias = Artist.get_or_create_shell(
                artist['id'], html_unescape(artist['name']), self.retrieved)
            TorrentArtist(
                artist=what_artist,
                artist_alias=artist_alias,
                torrent_group=self,
                importance=importance,
            ).save()

    def delete(self, *args, **kwargs):
        torrent_artists = list(self.torrentartist_set.all())
        super(TorrentGroup, self).delete(*args, **kwargs)
        for torrent_artist in torrent_artists:
            if torrent_artist.artist_alias is not None:
                if torrent_artist.artist_alias.torrentartist_set.count() == 0:
                    torrent_artist.artist_alias.delete()
            if torrent_artist.artist.torrentartist_set.count() == 0:
                torrent_artist.artist.delete()

    @classmethod
    def update_if_newer(cls, group_id, retrieved, data_dict, torrents_dict=None):
        try:
            group = TorrentGroup.objects.get(id=group_id)
            if retrieved < group.retrieved:
                return group
        except TorrentGroup.DoesNotExist:
            group = TorrentGroup(
                id=group_id
            )
        group.retrieved = retrieved
        group.wiki_body = data_dict['wikiBody']
        group.wiki_image = html_unescape(data_dict['wikiImage'])
        if data_dict.get('musicInfo'):
            group.joined_artists = get_artists(data_dict['musicInfo'])
        group.name = html_unescape(data_dict['name'])
        group.year = data_dict['year']
        group.record_label = html_unescape(data_dict['recordLabel'])
        group.catalogue_number = html_unescape(data_dict['catalogueNumber'])
        group.release_type = data_dict['releaseType']
        group.category_id = data_dict['categoryId']
        group.category_name = data_dict['categoryName']
        group.time = parse_db_datetime(data_dict['time'])
        group.vanity_house = data_dict['vanityHouse']
        group.info_json = json_dumps(data_dict)
        if torrents_dict is not None:
            group.torrents_json = json_dumps(torrents_dict)
        else:
            group.torrents_json = None
        group.save()

        if data_dict.get('musicInfo'):
            with transaction.atomic():
                group.artists.clear()
                group.add_artists(1, data_dict['musicInfo']['artists'])
                group.add_artists(2, data_dict['musicInfo']['with'])
                group.add_artists(3, data_dict['musicInfo']['remixedBy'])
                group.add_artists(4, data_dict['musicInfo']['composers'])
                group.add_artists(5, data_dict['musicInfo']['conductor'])
                group.add_artists(6, data_dict['musicInfo']['dj'])
                group.add_artists(7, data_dict['musicInfo']['producer'])
        return group


class TrackerTorrent(TrackerTorrentBase):
    torrent_group = models.ForeignKey(TorrentGroup, null=True)
    info_json = models.TextField()
    category_id = models.IntegerField()
    release_type_id = models.IntegerField()
    media = models.CharField(max_length=32)
    format = models.CharField(max_length=32)
    encoding = models.CharField(max_length=32)
    size_bytes = models.BigIntegerField()
    user_id = models.IntegerField(db_index=True)

    @cached_property
    def info(self):
        return WhatTorrentInfo(self.info_dict)

    @cached_property
    def info_dict(self):
        return json_loads(self.info_json)

    def _update_fields(self):
        info = self.info
        self.id = info.id
        self.category_id = info.category_id
        self.release_type_id = info.release_type_id
        self.media = info.media
        self.format = info.format
        self.encoding = info.encoding
        self.size_bytes = info.size
        self.user_id = info.user_id

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.torrent_group = TorrentGroup.update_if_newer(
                self.info.group_id, self.retrieved, self.info_dict['group'])
        self._update_fields()
        super(TrackerTorrent, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super(TrackerTorrent, self).delete(*args, **kwargs)
        if self.torrent_group.trackertorrent_set.count() == 0:
            self.torrent_group.delete()

    @classmethod
    def from_response(cls, response, torrent_info):
        torrent = TrackerTorrent(
            announces=torrent_info.announces,
            info_hash=torrent_info.info_hash,
            retrieved=timezone.now(),
        )
        torrent.info_json = json_dumps(response)
        torrent.id = torrent.info.id
        torrent._update_fields()
        return torrent


class LoginCache(models.Model):
    cookies = models.TextField()
    authkey = models.TextField()
    passkey = models.TextField()

    @classmethod
    def get(cls):
        return LoginCache.objects.get(id=1)

    @classmethod
    def set(cls, login_cache):
        login_cache.id = 1
        login_cache.save()


class Settings(models.Model):
    user_id = models.IntegerField()
    username = models.CharField(max_length=128)
    password = models.CharField(max_length=128)
    monitor_freeleech = models.BooleanField(default=False)

    @classmethod
    def get(cls):
        try:
            return Settings.objects.get(id=1)
        except Settings.DoesNotExist:
            raise Settings.DoesNotExist('What.CD settings not configured')

    @classmethod
    def set(cls, settings):
        settings.id = 1
        settings.save()


class FreeleechTorrent(models.Model):
    group_id = models.IntegerField()
    torrent_id = models.IntegerField()
    group_json = models.TextField()
    torrent_json = models.TextField()

    @cached_property
    def group(self):
        return json_loads(self.group_json)

    @cached_property
    def torrent(self):
        return json_loads(self.torrent_json)
