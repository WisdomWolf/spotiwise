"""
A wrapper around the Spotipy library that returns objects instead of raw JSON
"""

import spotipy

# These would be imported from .models in the actual implementation
# but for the prototype we'll use placeholders
class SpotiwiseTrack:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        # Example of extracting useful properties
        self.artist = kwargs.get('artists', [{}])[0].get('name')

class SpotiwiseArtist:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class SpotiwiseAlbum:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class SpotiwisePlaylist:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class SpotiwiseUser:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


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
        return SpotiwiseUser(**raw_user)
    
    # Additional methods would follow this pattern