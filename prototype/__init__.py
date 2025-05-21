"""
Spotiwise - A Spotify API wrapper that returns Python objects
"""

__version__ = '0.11.0'

# Import from spotipy
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth, SpotifyImplicitGrant

# Import spotiwise client and models
from .client import Spotify
from .models import (
    SpotiwiseTrack,
    SpotiwiseAlbum,
    SpotiwiseArtist, 
    SpotiwisePlaylist,
    SpotiwiseUser,
    SpotiwiseItem,
    SpotiwisePlayback
)

# For backwards compatibility
from spotipy.exceptions import SpotifyException