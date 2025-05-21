"""
Example of using the refactored Spotiwise library
"""

import os
import sys
from pprint import pprint

# Add parent directory to Python path for imports to work in this example
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from spotiwise prototype
from prototype import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

def main():
    """Run example code demonstrating the refactored Spotiwise library"""
    
    # Get client ID and secret from environment variables
    client_id = os.getenv('SPOTIPY_CLIENT_ID')
    client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("Error: Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables")
        sys.exit(1)
    
    # Create client credentials manager
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    
    # Create spotiwise client
    sp = Spotify(auth_manager=auth_manager)
    
    # Get a track by ID
    track_id = '4iV5W9uYEdYUVa79Axb7Rh'  # "Gangsta's Paradise" by Coolio
    track = sp.track(track_id)
    
    # Print track details
    print("Track Details:")
    print(f"Name: {track.name}")
    print(f"Artist: {track.artist}")
    print(f"Album: {track.album.name}")
    print(f"Duration: {track.duration}s")
    print(f"URI: {track.uri}")
    print()
    
    # Get an artist by ID
    artist_id = '3jOstUTkEu2JkjvRdBA5Gu'  # David Bowie
    artist = sp.artist(artist_id)
    
    # Print artist details
    print("Artist Details:")
    print(f"Name: {artist.name}")
    print(f"ID: {artist.id}")
    print(f"URI: {artist.uri}")
    print()
    
    # Get an album by ID
    album_id = '0sNOF9WDwhWunNAHPD3Baj'  # In Rainbows
    album = sp.album(album_id)
    
    # Print album details
    print("Album Details:")
    print(f"Name: {album.name}")
    print(f"Artist: {album.artist}")
    print(f"Type: {album.album_type}")
    print(f"URI: {album.uri}")
    
    # This shows how the object-oriented approach provides clear, intuitive access to data
    # without having to navigate through dictionaries.

if __name__ == "__main__":
    main()