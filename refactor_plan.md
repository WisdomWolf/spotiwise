# Spotiwise Refactor Plan

## Current State

Spotiwise is currently a fork of the spotipy library with modifications to return Python objects instead of raw JSON. The key patterns are:

1. Original spotipy methods prefixed with `_` (e.g., `_track()`) that return raw JSON
2. Wrapper methods without prefix (e.g., `track()`) that call the prefixed methods and wrap results in object classes
3. Object classes in `object_classes.py` that provide rich functionality on top of the API data

## New Architecture

### High-Level Overview

The new architecture will use spotipy as a dependency instead of a fork. This involves:

1. A wrapper client class that extends spotipy's Spotify client
2. Preserved object model classes from the current implementation
3. Clean separation between the spotipy interface and spotiwise enhancements

### Key Components

#### 1. Client Class

```python
# client.py
import spotipy
from .models import (
    SpotiwiseTrack, 
    SpotiwiseArtist, 
    SpotiwiseAlbum, 
    SpotiwisePlaylist,
    SpotiwiseUser,
    SpotiwiseItem,
    SpotiwisePlayback
)

class Spotify(spotipy.Spotify):
    """Spotiwise client that extends the spotipy Spotify client.
    
    This client overrides methods to return object instances instead of raw JSON.
    """
    
    def track(self, track_id):
        """Get a track by its ID and return as a SpotiwiseTrack object.
        
        Parameters:
            - track_id: A track URI, URL or ID
        """
        # Call the parent class method to get raw JSON
        raw_track = super().track(track_id)
        # Wrap the raw JSON in a SpotiwiseTrack object
        return SpotiwiseTrack(**raw_track)
    
    def tracks(self, tracks, market=None):
        """Get multiple tracks and return as SpotiwiseTrack objects.
        
        Parameters:
            - tracks: A list of track URIs, URLs or IDs
            - market: An ISO 3166-1 alpha-2 country code
        """
        raw_result = super().tracks(tracks, market=market)
        return [SpotiwiseTrack(**track) for track in raw_result['tracks']]
    
    def artist(self, artist_id):
        """Get an artist by ID and return as a SpotiwiseArtist object.
        
        Parameters:
            - artist_id: An artist URI, URL or ID
        """
        raw_artist = super().artist(artist_id)
        return SpotiwiseArtist(**raw_artist)
    
    def artists(self, artists):
        """Get multiple artists and return as SpotiwiseArtist objects.
        
        Parameters:
            - artists: A list of artist URIs, URLs or IDs
        """
        raw_result = super().artists(artists)
        return [SpotiwiseArtist(**artist) for artist in raw_result['artists']]
    
    def album(self, album_id):
        """Get an album by ID and return as a SpotiwiseAlbum object.
        
        Parameters:
            - album_id: An album URI, URL or ID
        """
        raw_album = super().album(album_id)
        return SpotiwiseAlbum(**raw_album)
    
    def albums(self, albums):
        """Get multiple albums and return as SpotiwiseAlbum objects.
        
        Parameters:
            - albums: A list of album URIs, URLs or IDs
        """
        raw_result = super().albums(albums)
        return [SpotiwiseAlbum(**album) for album in raw_result['albums']]
    
    def user(self, user_id):
        """Get a user profile and return as a SpotiwiseUser object.
        
        Parameters:
            - user_id: A user ID
        """
        raw_user = super().user(user_id)
        return SpotiwiseUser(**raw_user, sp=self)
    
    def current_user_playlists(self, limit=50, offset=0):
        """Get current user playlists as SpotiwisePlaylist objects.
        
        Parameters:
            - limit: The maximum number of playlists to return
            - offset: The index of the first playlist to return
        """
        raw_result = super().current_user_playlists(limit=limit, offset=offset)
        return [SpotiwisePlaylist(sp=self, **playlist) for playlist in raw_result['items']]
    
    # More methods would be implemented following this pattern...
```

#### 2. Object Models

```python
# models.py (renamed from object_classes.py)

class _SpotiwiseBase(object):
    # Largely unchanged from current implementation
    # ...

class SpotiwiseArtist(_SpotiwiseBase):
    # Largely unchanged from current implementation
    # ...

class SpotiwiseAlbum(_SpotiwiseBase):
    # Largely unchanged from current implementation
    # ...

class SpotiwiseTrack(_SpotiwiseBase):
    # Largely unchanged from current implementation
    # ...

class SpotiwisePlayback(_SpotiwiseBase):
    # Largely unchanged from current implementation
    # ...

class SpotiwiseItem(_SpotiwiseBase):
    # Largely unchanged from current implementation
    # ...

class SpotiwisePlaylist(_SpotiwiseBase):
    # Largely unchanged from current implementation
    # Remove dependencies on internal methods
    # Adjust track loading to use passed spotipy client
    # ...

class SpotiwiseUser(_SpotiwiseBase):
    # Largely unchanged from current implementation
    # Adjust to use passed spotipy client for any API calls
    # ...

class SpotiwiseUserFactory:
    # Largely unchanged from current implementation
    # ...
```

#### 3. Package Structure

```
spotiwise/
├── __init__.py           # Exports client and models
├── client.py             # Contains Spotify class that extends spotipy.Spotify
├── models.py             # Contains Spotiwise object classes (renamed from object_classes.py)
├── exceptions.py         # Any custom exceptions not in spotipy
├── util.py               # Any utility functions not provided by spotipy
└── constants.py          # Any constants needed
```

### Initialization and Authentication

The client initialization would be simplified since we can leverage spotipy's authentication:

```python
import spotiwise

# Using client credentials flow
from spotipy.oauth2 import SpotifyClientCredentials

client_id = 'your-spotify-client-id'
client_secret = 'your-spotify-client-secret'

auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotiwise.Spotify(auth_manager=auth_manager)

# Get a track as a SpotiwiseTrack object
track = sp.track('spotify:track:4iV5W9uYEdYUVa79Axb7Rh')
print(f"Track: {track.name} by {track.artist}")
```

## Migration Strategy

### Step 1: Add spotipy as a Dependency

Update pyproject.toml to include spotipy as a dependency:

```toml
[tool.poetry.dependencies]
python = ">=3.6"
requests = ">=2.3.0"
six = ">=1.10.0"
spotipy = "^2.23.0"  # Use latest stable version
```

### Step 2: Create New Module Structure

1. Rename `object_classes.py` to `models.py`
2. Create a new `client.py` that extends spotipy's client
3. Update `__init__.py` to import from the new modules

### Step 3: Implement the Client

1. Start with the most commonly used methods (tracks, artists, albums, playlists)
2. Add more methods progressively
3. Ensure comprehensive test coverage for each method

### Step 4: Adapt Object Models

1. Remove dependencies on internal API methods
2. Adjust object instantiation to work with spotipy responses
3. Ensure models work with the new client

### Step 5: Remove Duplicated Code

1. Remove code duplicated from spotipy
2. Remove deprecated methods or implement them as thin wrappers

### Step 6: Test and Validate

1. Ensure all tests pass with the new implementation
2. Verify API responses are correctly wrapped in objects
3. Check for any regressions in functionality

### Step 7: Update Documentation and Examples

1. Update documentation to reflect the new architecture
2. Update examples to show how to use the new client

## Potential Challenges and Considerations

### 1. API Compatibility

Spotipy may have updated its API since spotiwise was forked. We need to ensure compatibility with the latest spotipy version or handle differences appropriately.

### 2. Custom Methods

If spotiwise has added custom methods not in spotipy, these will need to be implemented on top of spotipy's functionality.

### 3. Object Initialization

Spotipy's JSON responses may have changed in structure, requiring adjustments to how objects are initialized.

### 4. Backward Compatibility

Ensure backward compatibility for existing spotiwise users, possibly through a compatibility layer or clear migration guide.

### 5. Authentication Flows

Make sure all authentication flows supported by spotiwise are preserved when switching to spotipy's authentication.

### 6. Performance

The wrapper approach adds a layer of object instantiation that might impact performance slightly. This should be monitored and optimized if necessary.

## Conclusion

This refactoring will significantly reduce maintenance burden by leveraging spotipy as a dependency rather than a fork. It will allow spotiwise to focus on its value-add (the object model) while benefiting from spotipy's ongoing maintenance and updates.
