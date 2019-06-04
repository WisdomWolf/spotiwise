from datetime import date

class _SpotiwiseBase(object):

    sort_keys = ['id', 'name']
    repr_attributes = None

    def __init__(self, href=None, type=None, uri=None):
        self.href = href
        self.type = type
        self.uri = uri

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

    def _sort(self, key):
        '''Used to ensure certain attributes are listed first'''
        key = key.split(':')[0].lower()
        try:
            return self.sort_keys.index(key)
        except ValueError:
            return float('inf')


class SpotiwiseArtist(_SpotiwiseBase):

    repr_attributes = ['name']

    def __init__(self, id, name, external_urls=None, href=None, type=None, uri=None, *args, **kwargs):
        self.id = id
        self.name = name
        self.external_urls=external_urls
        self.href = href
        self.type = type
        self.uri = uri
        self._args = args
        self._kwargs = kwargs


class SpotiwiseAlbum(_SpotiwiseBase):

    repr_attributes = ['name', 'artist']

    def __init__(self, id, name, album_type=None, artists=None, available_markets=None, external_urls=None, href=None, images=None, type=None, uri=None, *args, **kwargs):
        self.id = id
        self.name = name
        self.external_urls = external_urls or []
        self._artists = [SpotiwiseArtist(**artist) if not isinstance(artist, SpotiwiseArtist) else artist for artist in artists]
        self.artist = self._artists[0].name
        self.available_markets = available_markets or []
        self.href = href
        self.images = images or []
        self.type = type
        self.uri = uri
        self._args = args
        self._kwargs = kwargs


class SpotiwiseTrack(_SpotiwiseBase):

    repr_attributes = ['name', 'artist']

    def __init__(self, id, name, album, artists, available_markets=None, disc_number=None,
    duration_ms=0, explicit=False, external_ids=None, external_urls=None, href=None,
    popularity=None, preview_url=None, track_number=None, type=None, uri=None, episode=False, is_local=False, track=True, *args, **kwargs):
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
        self.href = href
        self.popularity = popularity
        self.preview_url = preview_url
        self.track_number = track_number
        self.type = type
        self.uri = uri
        self.playcount = 0
        self._args = args
        self._kwargs = kwargs


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

    def __init__(self, track, added_at=None, added_by='', is_local=False, *args, **kwargs):
        self.track = track if isinstance(track, SpotiwiseTrack) else SpotiwiseTrack(**track)
        self.added_at = added_at
        self.added_by = added_by if isinstance(added_by, SpotiwiseUser) else SpotiwiseUser(**added_by)
        self.is_local = is_local


class SpotiwisePlaylist(_SpotiwiseBase):

    repr_attributes = ['name', 'owner', 'collaborative', 'description']

    def __init__(self, id, name, owner, collaborative=False, description=None, external_urls=None,
    followers=None, href=None, images=None, public=True, snapshot_id=None, tracks=None, type=None,
    uri=None, sp=None, precache=False, *args, **kwargs):
        self.id = id
        self.name = name
        self.owner = owner if isinstance(owner, SpotiwiseUser) else SpotiwiseUser(**owner, sp=sp)
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
        try:
            self.items = [SpotiwiseItem(**item) for item in self._tracks.get('items')]
        except TypeError: # Uninstantiated playlist (possibly from current_user_playlists())
            self.items = None
        if precache:
            while self._tracks['next']:
                self._tracks = sp.next(self._tracks)
                self.items.extend([SpotiwiseItem(**item) for item in self._tracks.get('items')])
        try:
            self.tracks = [item.track for item in self.items]
        except TypeError:
            self.tracks = self._tracks

    def __len__(self):
        return len(self.tracks)


class SpotiwiseUser(_SpotiwiseBase):

    repr_attributes = ['display_name']

    def __init__(self, id, display_name=None, href=None, external_urls=None, images=None, followers=None, 
                 type=None, uri=None, sp=None):
        self.id = id
        if sp:
            user = SpotiwiseUser(**sp._user(self.id))
            for k, v in user.__dict__.items():
                setattr(self, k, v)
        else:
            self.display_name = display_name or '__{}__'.format(self.id)
            self.href = href
            self.external_urls = external_urls
            self.images = images
            self.followers = followers
            self.type = type
            self.uri = uri

    def __key(self):
        return (self.id, self.display_name, self.type, self.uri)

    def __eq__(x, y):
        return x.__key() == y.__key()

    def __hash__(self):
        return hash(self.__key())

