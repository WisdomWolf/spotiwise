from datetime import date
from logging import getLogger

import spotiwise

logger = getLogger(__name__)

class _SpotiwiseBase(object):

    sort_keys = ['id', 'name']
    repr_attributes = None

    def __init__(self, href=None, type=None, uri=None, sp=None, *args, **kwargs):
        self.href = href
        self.type = type
        self.uri = uri
        self.sp = sp
        self._args = args
        self._kwargs = kwargs

    def __repr__(self):
        repr_list = []
        repr_attributes = self.repr_attributes or self.__dict__.keys()
        for k in repr_attributes:
            try:
                v = getattr(self, k)
            except AttributeError:
                v = None
            if v:
                if isinstance(v, date):
                    v = '{:%m/%d/%Y}'.format(v)
                k = k.replace('_', ' ')
                repr_list.append('{}={}'.format(k, v))
        return '{}({})'.format(self.__class__.__name__, ', '.join(sorted(repr_list, key=self._sort)))

    def __eq__(self, other):
        if isinstance(other, _SpotiwiseBase):
            return self.uri == other.uri
        else:
            return False

    def _sort(self, key):
        '''Used to ensure certain attributes are listed first'''
        key = key.split(':')[0].lower()
        try:
            return self.sort_keys.index(key)
        except ValueError:
            return float('inf')


class SpotiwiseArtist(_SpotiwiseBase):

    repr_attributes = ['name']

    def __init__(self, id, name, external_urls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.name = name
        self.external_urls=external_urls


class SpotiwiseAlbum(_SpotiwiseBase):

    repr_attributes = ['name', 'artist']

    def __init__(self, id, name, album_type=None, artists=None, available_markets=None, external_urls=None, images=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.name = name
        self.external_urls = external_urls or []
        self._artists = [SpotiwiseArtist(**artist) if not isinstance(artist, SpotiwiseArtist) else artist for artist in artists]
        try:
            self.artist = self._artists[0].name
        except IndexError:
            logger.warning('Unable to parse artist name from %s.', artists)
            self.artist = artists
        self.available_markets = available_markets or []
        self.images = images or []


class SpotiwiseTrack(_SpotiwiseBase):

    repr_attributes = ['name', 'artist']

    def __init__(self, id, name, album, artists, available_markets=None, disc_number=None,
    duration_ms=0, explicit=False, external_ids=None, external_urls=None,
    popularity=None, preview_url=None, track_number=None, episode=False, is_local=False, track=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.name = name
        self.album = album if isinstance(album, SpotiwiseAlbum) else SpotiwiseAlbum(**album)
        self._artists = [SpotiwiseArtist(**artist) if not isinstance(artist, SpotiwiseArtist) else artist for artist in artists]
        self.artist = self._artists[0].name
        self.available_markets = available_markets or []
        self.disc_number = disc_number
        self.duration_ms = duration_ms
        self.duration = self.duration_ms // 1000
        self.explicit = explicit
        self.external_ids = external_ids
        self.external_urls = external_urls
        self.popularity = popularity
        self.preview_url = preview_url
        self.track_number = track_number
        self.playcount = 0

class SpotiwisePlayback(_SpotiwiseBase):

    def __init__(self, item, timestamp=None, progress_ms=None, is_playing=False, context=None, *args, **kwargs):
        self.track = item if isinstance(item, SpotiwiseTrack) else SpotiwiseTrack(**item) # will eventually point to self.item.track
        self.item = item if isinstance(item, SpotiwiseTrack) else SpotiwiseTrack(**item)
        self.ttrack = self.item.track # will replace track attribute eventually
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


class SpotiwiseItem(_SpotiwiseBase):

    repr_attributes = ['track', 'added_at', 'added_by']

    def __init__(self, track, added_at=None, added_by='', is_local=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.track = track if isinstance(track, SpotiwiseTrack) else SpotiwiseTrack(**track)
        self.added_at = added_at
        self.added_by = added_by if isinstance(added_by, SpotiwiseUser) else SpotiwiseUser(sp=self.sp, **added_by)
        self.is_local = is_local

    def __eq__(self, other):
        if isinstance(other, SpotiwiseItem):
            return self.track == other.track \
                and self.added_at == other.added_at \
                and self.added_by == other.added_by
        else:
            return False


class SpotiwisePlaylist(_SpotiwiseBase):

    repr_attributes = ['name', 'owner', 'collaborative', 'description']

    def __init__(self, id, name, owner, collaborative=False, description=None, external_urls=None,
    followers=None, images=None, public=True, snapshot_id=None, tracks=None,
    precache=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.name = name
        self.owner = owner if isinstance(owner, SpotiwiseUser) else SpotiwiseUser(sp=self.sp, **owner)
        self.collaborative = collaborative
        self.description = description
        self.external_urls = external_urls
        self.followers = followers
        self.images = images
        self.public = public
        self.snapshot_id = snapshot_id
        self._tracks = tracks
        try:
            self.items = [SpotiwiseItem(**item) for item in self._tracks.get('items')]
        except TypeError: # Uninstantiated playlist (possibly from current_user_playlists())
            self.items = []
        if precache:
            self.load_tracks()
            #while self._tracks['next']:
             #   self._tracks = sp.next(self._tracks)
             #    self.items.extend([SpotiwiseItem(**item) for item in self._tracks.get('items')])
        try:
            self.tracks = [item.track for item in self.items]
        except TypeError:
            self.tracks = self._tracks

    def __len__(self):
        return self._tracks.get('total', -1)

    def load_tracks(self, sp=None):
        sp = sp or self.sp
        if not sp:
            raise RuntimeError('Need a spotify client reference to load tracks')

        self.items = self.items or []

        if 'next' not in self._tracks:
            if 'href' in self._tracks:
                self._tracks = sp._get(self._tracks.get('href'))
                self.items = [SpotiwiseItem(sp=sp, **item) for item in self._tracks.get('items')]
        while self._tracks.get('next'):
            self._tracks = sp.next(self._tracks)
            self.items.extend([SpotiwiseItem(sp=sp, **item) for item in self._tracks.get('items')])

        try:
            self.tracks = [item.track for item in self.items]
        except TypeError:
            self.tracks = self._tracks


class SpotiwiseUser(_SpotiwiseBase):

    repr_attributes = ['display_name']

    def __init__(self, id, display_name=None, images=None, followers=None,
                 external_urls=None, *args, **kwargs):
        self.id = id
        super().__init__(*args, **kwargs)
        if self.sp:
            sp = self.sp
            try:
                user = SpotiwiseUser(**sp._user(self.id))
                for k, v in user.__dict__.items():
                    setattr(self, k, v)
            except spotiwise.SpotifyException:
                self.display_name = display_name or f'__{self.id}__'
        else:
            self.display_name = display_name or '__{}__'.format(self.id)
            self.external_urls = external_urls
            self.images = images
            self.followers = followers

    def __key(self):
        return (self.id, self.display_name, self.type, self.uri)

    def __eq__(x, y):
        return x.__key() == y.__key()

    def __hash__(self):
        return hash(self.__key())

