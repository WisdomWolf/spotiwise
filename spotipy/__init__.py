version = {}
with open('version.py') as f:
    exec(f.read(), version)
VERSION=version['__version__']
from .client import Spotify, SpotifyException
