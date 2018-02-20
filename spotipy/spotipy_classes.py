from datetime import date
import logging
import arrow
from apscheduler.schedulers.background import BackgroundScheduler

class _SpotipyBase(object):

    def __init__(self, href=None, type=None, uri=None):
        self.href = href
        self.type = type
        self.uri = uri

    def __repr__(self):
        repr_list = []
        for k, v in self.__dict__.items():
            if v:
                if isinstance(v, date):
                    v = '{:%m/%d/%Y}'.format(v)
                k = k.replace('_', ' ')
                repr_list.append('{}={}'.format(k, v))
        return '{}({})'.format(self.__class__.__name__, ', '.join(sorted(repr_list, key=self._sort)))

    @staticmethod
    def _sort(key):
        '''Used to ensure certain attributes are listed first'''
        key = key.split(':')[0].lower()
        sort_keys = ['id', 'name'] # Should probably be a class variable so that it can be easily overridden
        try:
            return sort_keys.index(key)
        except ValueError:
            return float('inf')



class SpotipyArtist(_SpotipyBase):

    def __init__(self, id, name, external_urls=None, href=None, type=None, uri=None, *args, **kwargs):
        self.id = id
        self.name = name
        self.external_urls=external_urls
        self.href = href
        self.type = type
        self.uri = uri
        self._args = args
        self._kwargs = kwargs


class SpotipyAlbum(_SpotipyBase):

    def __init__(self, id, name, album_type=None, artists=None, available_markets=None, external_urls=None, href=None, images=None, type=None, uri=None, *args, **kwargs):
        self.id = id
        self.name = name
        self.external_urls = external_urls or []
        self._artists = [SpotipyArtist(**artist) if not isinstance(artist, SpotipyArtist) else artist for artist in artists]
        self.artist = self._artists[0].name
        self.available_markets = available_markets or []
        self.href = href
        self.images = images or []
        self.type = type
        self.uri = uri
        self._args = args
        self._kwargs = kwargs


class SpotipyTrack(_SpotipyBase):

    def __init__(self, id, name, album, artists, available_markets=None, disc_number=None, 
    duration_ms=0, explicit=False, external_ids=None, external_urls=None, href=None, 
    popularity=None, preview_url=None, track_number=None, type=None, uri=None, *args, **kwargs):
        #print('__init__ received')
       # for param, value in locals().items():
          #  print('{}: {}\n'.format(param, value))
        self.id = id
        self.name = name
        if isinstance(album, SpotipyAlbum):
            self.album = album
        else:
            self.album = SpotipyAlbum(**album)
        self._artists = [SpotipyArtist(**artist) if not isinstance(artist, SpotipyArtist) else artist for artist in artists]
        self.artist = self._artists[0].name
        self.available_markets = available_markets or []
        self.disc_number = disc_number
        self.duration_ms = duration_ms
        self.duration = self.duration_ms // 1000
        self.explicit = explicit
        self.external_ids = external_ids
        self.external_urls = external_urls
        self.href = href
        self.popularity = popularity
        self.preview_url = preview_url
        self.track_number = track_number
        self.type = type
        self.uri = uri
        self.playcount = 0
        self._args = args
        self._kwargs = kwargs


class SpotipyPlayback(_SpotipyBase):

    def __init__(self, item, timestamp=None, progress_ms=None, is_playing=False, context=None, *args, **kwargs):
       # print('__init__ received')
     #   for param, value in locals().items():
         #   print('{}: {}\n'.format(param, value))
        self.track = item if isinstance(item, SpotipyTrack) else SpotipyTrack(**item)
        self.timestamp = timestamp or time.time()
        self.epoch_timestamp = self.timestamp // 1000
        self.progress_ms = progress_ms or 0
        self.is_playing = is_playing
        self.context = context
        self._args = args
        self._kwargs = kwargs

    @property
    def progress(self):
        return round(self.progress_ms / self.track.duration_ms * 100, 0)


class SpotipyItem(_SpotipyBase):

    def __init__(self, track, added_at=None, added_by='', is_local=False):
        self.track = track if isinstance(track, SpotipyTrack) else SpotipyTrack(**track)
        self.added_at = added_at
        self.added_by = added_by
        self.is_local = is_local


class SpotipyPlaylist(_SpotipyBase):

    def __init__(self, id, name, owner, collaborative=False, description=None, external_urls=None, 
    followers=None, href=None, images=None, public=True, snapshot_id=None, tracks=None, type=None, 
    uri=None, sp=None, precache=False):
        self.id = id
        self.name = name
        self.owner = owner
        self.collaborative = collaborative
        self.description = description
        self.external_urls = external_urls
        self.followers = followers
        self.href = href
        self.images = images
        self.public = public
        self.snapshot_id = snapshot_id
        self._tracks = tracks
        self.type = type
        self.uri = uri
        self.tracks = [SpotipyItem(**item) for item in self._tracks.get('items')]
        if precache:
            while self._tracks['next']:
                self._tracks = sp.next(self._tracks)
                self.tracks.extend([SpotipyItem(**item) for item in self._tracks.get('items')])


def mad_parser(thing):
    results = {}
    if isinstance(thing, dict):
        for k, v in thing.items():
            results[k] = mad_parser(v)
            if thing.get('type') and thing.get('id'):
                return SpotipyTypes[thing['type']](**thing)
        return results
    elif isinstance(thing, list):
        things = []
        for x in thing:
            things.append(mad_parser(x))
        return things
    else:
        return thing


SpotipyTypes = {
    'album': SpotipyAlbum,
    'track': SpotipyTrack,
    'artist': SpotipyArtist
}

def get_currently_playing():
    current = currently_playing()
    track = current.get('item')
    a = track.get('album')
    album = SpotipyAlbum(a.get('id'), a.get('name'), a.get('album_type'), )


def scrobbler(sp, lastfm_user, lastfm_network):
    sp_now_playing = create_lastfm_tuple(sp.currently_playing())
    lastfm_now_playing = lastfm_user.get_now_playing()
    if sp_now_playing and not lastfm_now_playing:
        if playback_percentage(sp.currently_playing()) > 70:
            print('should scrobble {}'.format(sp_now_playing.title))
            lastfm_network.scrobble(*sp_now_playing)
        else:
            print('updating lastfm now playing')
            lastfm_network.update_now_playing(sp_now_playing.artist, sp_now_playing.title,
                        sp_now_playing.album, sp_now_playing.album_artist, sp_now_playing.duration)
    elif sp_now_playing.title != lastfm_now_playing.title:
        print('Spotify: {}\nLast.FM: {}'.format(sp_now_playing.title, lastfm_now_playing.title))
        print('updating lastfm')
        lastfm_network.update_now_playing(sp_now_playing.artist, sp_now_playing.title, sp_now_playing.album, sp_now_playing.album_artist, sp_now_playing.duration)
    else:
        print('Looks good!')


class Scrobbler(object):
    def __init__(self, spotify, lastfm_user, lastfm_network, current_track=None):
        self.previous_playback = None
        self.spotify = spotify
        self.lastfm_user = lastfm_user
        self.lastfm_network = lastfm_network
        self.current_playback = current_track or SpotipyPlayback(**self.spotify.currently_playing()) if self.spotify.currently_playing() else None
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def update_track(self, track=None):
        playback_event = track or SpotipyPlayback(**self.spotify.currently_playing()) if self.spotify.currently_playing() else None
        if not self.current_playback:
            self.current_playback = playback_event
        if playback_event and playback_event.is_playing:
            track = playback_event.track
            lastfm_now_playing = self.lastfm_user.get_now_playing()
            if not lastfm_now_playing or lastfm_now_playing.title != track.name:
                logging.info('updating lastfm now playing')
                self.lastfm_network.update_now_playing(artist=track.artist, title=track.name,
                        album=track.album.name, album_artist=track.album.artist, duration=track.duration)
            # else:
            #     print('lastfm appears to show {} is playing'.format(track.name))
            if self.current_playback.track.name != track.name:
                logging.info('Looks like track has changed from {} to {}'.format(self.current_playback.track.name, track.name))
                self.previous_playback = self.current_playback
                self.current_playback = playback_event
                self.scheduler.add_job(self.scrobble_check, 'date', run_date=arrow.now().shift(seconds=30).datetime)
            else:
                self.current_playback = playback_event
        # else:
        #     print('nothing currently playing')

    def scrobble_check(self):
        previous_track = self.previous_playback.track
        # verify track in recently_played to honor 'private' session
        most_recent_spotify_track = SpotipyTrack(**self.spotify.current_user_recently_played(limit=1).get('items')[0].get('track')).name
        if previous_track.name == most_recent_spotify_track and \
                self.lastfm_user.get_recent_tracks(limit=2)[0].track.get_name() != previous_track.name:
            if self.previous_playback.progress > 70:
                logging.info('scrobbling: {}'.format(previous_track.name))
                self.lastfm_network.scrobble(artist=previous_track.artist, title=previous_track.name,
                    timestamp=self.previous_playback.epoch_timestamp, album=previous_track.album.name,
                    album_artist=previous_track.album.artist, duration=previous_track.duration)
            else:
                logging.warn('Not scrobbling previous song because it does not meet 70% threshold') 


def create_lastfm_tuple(spotify_now_playing):
    from collections import namedtuple
    NowPlaying = namedtuple('NowPlaying', ['artist', 'title', 'timestamp', 'album', 'album_artist', 'duration'])
    NowPlaying.__new__.__defaults__ = (None, None, None)
    track = spotify_now_playing.get('item')
    return NowPlaying(artist=track.get('artists')[0].get('name'), title=track.get('name'), timestamp=spotify_now_playing.get('timestamp')//1000, album=track.get('album').get('name'),
        album_artist=track.get('album').get('artists')[0].get('name'), duration=track.get('duration_ms') // 1000)


if __name__ == '__main__':
    import json
    with open('example_track.json') as f:
        example_track = json.load(f)
