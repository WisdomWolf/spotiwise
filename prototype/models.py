"""
Object model classes for Spotiwise
"""

from datetime import date
from logging import getLogger

logger = getLogger(__name__)


class _SpotiwiseBase(object):
    """Base class for all Spotiwise objects"""

    sort_keys = ['id', 'name']
    repr_attributes = None

    def __init__(self, href=None, type=None, uri=None, sp=None, *args, **kwargs):
        self.href = href
        self.type = type
        self.uri = uri
        self.sp = sp
        self._args = args
        self._kwargs = kwargs

    @property
    def _csv_header(self):
        cols = []
        for attr in sorted(self.repr_attributes, key=self._sort):
            if attr == 'track':
                from .models import SpotiwiseTrack  # Avoid circular import
                cols.extend(SpotiwiseTrack.repr_attributes)
            else:
                cols.append(attr)
        return [','.join(cols)]

    @property
    def _repr_dict(self):
        repr_dict = {}
        repr_attributes = self.repr_attributes or vars(self).keys()
        for key in repr_attributes:
            try:
                val = getattr(self, key)
            except AttributeError:
                val = None
            if val:
                if isinstance(val, date):
                    val = f'{val:%m/%d/%Y}'
                key = key.replace('_', ' ')
                repr_dict[key] = val
        return repr_dict

    def __repr__(self):
        repr_list = [f'{key}={repr(value)}' for key, value in self._repr_dict.items()]
        return f"{self.__class__.__name__}({', '.join(sorted(repr_list, key=self._sort))})"

    def __eq__(self, other):
        if isinstance(other, _SpotiwiseBase):
            return self.uri == other.uri
        else:
            return False
        
    def __str__(self):
        values = self._repr_dict.values()
        return ','.join([f'{x}' for x in values])

    def _sort(self, key):
        '''Used to ensure certain attributes are listed first'''
        key = key.split(':')[0].lower()
        try:
            return self.sort_keys.index(key)
        except ValueError:
            return float('inf')


class SpotiwiseArtist(_SpotiwiseBase):
    """Class representing a Spotify artist"""

    repr_attributes = ['name']

    def __init__(self, id, name, external_urls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.name = name
        self.external_urls = external_urls


class SpotiwiseAlbum(_SpotiwiseBase):
    """Class representing a Spotify album"""

    repr_attributes = ['name', 'artist']

    def __init__(self, id, name, album_type=None, artists=None, available_markets=None, external_urls=None, images=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.name = name
        self.external_urls = external_urls or []
        from .models import SpotiwiseArtist  # Avoid circular import
        self._artists = [SpotiwiseArtist(**artist) if not isinstance(artist, SpotiwiseArtist) else artist for artist in (artists or [])]
        try:
            self.artist = self._artists[0].name
        except IndexError:
            logger.warning('Unable to parse artist name from %s.', artists)
            self.artist = artists
        self.available_markets = available_markets or []
        self.images = images or []


class SpotiwiseTrack(_SpotiwiseBase):
    """Class representing a Spotify track"""

    repr_attributes = ['name', 'artist', 'id']

    def __init__(
        self,
        id, 
        name,
        album=None,
        artists=None,
        available_markets=None,
        disc_number=None,
        duration_ms=0,
        explicit=False,
        external_ids=None,
        external_urls=None,
        popularity=None,
        preview_url=None,
        track_number=None,
        episode=False,
        is_local=False,
        track=True,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.id = id
        self.name = name
        from .models import SpotiwiseAlbum  # Avoid circular import
        self.album = album if isinstance(album, SpotiwiseAlbum) or album is None else SpotiwiseAlbum(**album)
        from .models import SpotiwiseArtist  # Avoid circular import
        self._artists = [SpotiwiseArtist(**artist) if not isinstance(artist, SpotiwiseArtist) else artist for artist in (artists or [])]
        self.artist = self._artists[0].name if self._artists else None
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
    """Class representing playback state"""

    def __init__(self, item=None, timestamp=None, progress_ms=None, is_playing=False, context=None, *args, **kwargs):
        import time
        from .models import SpotiwiseTrack  # Avoid circular import
        self.track = item if isinstance(item, SpotiwiseTrack) else (SpotiwiseTrack(**item) if item else None)
        self.item = self.track  # For API compatibility
        self.timestamp = timestamp or time.time()
        self.epoch_timestamp = self.timestamp // 1000
        self.progress_ms = progress_ms or 0
        self.is_playing = is_playing
        self.context = context
        self._args = args
        self._kwargs = kwargs

    @property
    def progress(self):
        if not self.track or not self.track.duration_ms:
            return 0
        return round(self.progress_ms / self.track.duration_ms * 100, 0)


class SpotiwiseUser(_SpotiwiseBase):
    """Class representing a Spotify user"""

    repr_attributes = ['display_name']

    def __init__(self, id, display_name=None, images=None, followers=None,
                 external_urls=None, *args, **kwargs):
        self.id = id
        super().__init__(*args, **kwargs)
        # Simplified implementation without making API calls
        self.display_name = display_name or f'__{self.id}__'
        self.external_urls = external_urls
        self.images = images
        self.followers = followers

    @property
    def __key(self):
        return self.id, self.display_name, self.type, self.uri

    def __eq__(self, other):
        if isinstance(other, SpotiwiseUser):
            return self.__key == other.__key
        return False

    def __hash__(self):
        return hash(self.__key)
    
    def __str__(self):
        return self.display_name


class SpotiwiseUserFactory:
    """Factory for creating SpotiwiseUser instances"""
    
    registry = {}

    @classmethod
    def get_instance(cls, *args, **kwargs):
        id_ = kwargs.get('id')
        if id_ is None:
            raise RuntimeError('Must provide an id')
        if id_ in cls.registry:
            instance = cls.registry[id_]
        else:
            instance = SpotiwiseUser(*args, **kwargs)
            cls.registry[id_] = instance
        return instance


class SpotiwiseItem(_SpotiwiseBase):
    """Class representing an item in a playlist"""

    repr_attributes = ['track', 'added_at', 'added_by']

    def __init__(self, track=None, added_at=None, added_by=None, is_local=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import SpotiwiseTrack  # Avoid circular import
        self.track = track if isinstance(track, SpotiwiseTrack) else (SpotiwiseTrack(**track) if track else None)
        self.added_at = added_at
        from .models import SpotiwiseUser, SpotiwiseUserFactory  # Avoid circular import
        self.added_by = added_by if isinstance(added_by, SpotiwiseUser) else (
            SpotiwiseUserFactory.get_instance(**added_by) if added_by else None
        )
        self.is_local = is_local

    def __eq__(self, other):
        if isinstance(other, SpotiwiseItem):
            return self.track == other.track \
                and self.added_at == other.added_at \
                and self.added_by == other.added_by
        else:
            return False
        
    def __hash__(self):
        return hash(repr(self))


class SpotiwisePlaylist(_SpotiwiseBase):
    """Class representing a Spotify playlist"""

    repr_attributes = ['name', 'owner', 'collaborative', 'description']

    def __init__(
            self,
            id,
            name,
            owner=None,
            collaborative=False,
            description=None,
            external_urls=None,
            followers=None,
            images=None,
            public=True,
            snapshot_id=None,
            tracks=None,
            precache=False,
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.id = id
        self.name = name
        from .models import SpotiwiseUser, SpotiwiseUserFactory  # Avoid circular import
        self.owner = owner if isinstance(owner, SpotiwiseUser) else (
            SpotiwiseUserFactory.get_instance(**owner) if owner else None
        )
        self.collaborative = collaborative
        self.description = description
        self.external_urls = external_urls
        self.followers = followers
        self.images = images
        self.public = public
        self.snapshot_id = snapshot_id
        self._tracks = tracks or {}
        from .models import SpotiwiseItem  # Avoid circular import
        try:
            self.items = [SpotiwiseItem(**item) for item in self._tracks.get('items', [])]
        except (TypeError, AttributeError):  # Uninstantiated playlist
            self.items = []
        if precache and self.sp:
            self.load_tracks()
        try:
            self.tracks = [item.track for item in self.items]
        except (TypeError, AttributeError):
            self.tracks = []

    def __len__(self):
        return self._tracks.get('total', -1)
    
    def to_csv(self, file=None):
        """Export playlist to CSV format"""
        if not self.items:
            return ''
        result = self.items[0]._csv_header
        result.extend([str(item) for item in self.items])
        result = '\n'.join(result)
        if file:
            with open(file, 'w') as f:
                f.write(result)
        else:
            return result

    def load_tracks(self, sp=None):
        """Load all tracks in the playlist"""
        sp = sp or self.sp
        if not sp:
            raise RuntimeError('Need a spotify client reference to load tracks')

        self.items = self.items or []

        # Get initial tracks if we only have a href
        if 'next' not in self._tracks:
            if 'href' in self._tracks:
                self._tracks = sp._get(self._tracks.get('href'))
                from .models import SpotiwiseItem  # Avoid circular import
                self.items.extend([SpotiwiseItem(sp=sp, **item) for item in self._tracks.get('items', []) 
                                   if item.get('track') is not None])
        
        # Continue fetching if there are more pages
        while self._tracks.get('next'):
            self._tracks = sp.next(self._tracks)
            from .models import SpotiwiseItem  # Avoid circular import
            self.items.extend([SpotiwiseItem(sp=sp, **item) for item in self._tracks.get('items', []) 
                               if item.get('track') is not None])

        # Update the tracks list
        self.tracks = [item.track for item in self.items if item.track is not None]