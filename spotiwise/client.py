# -*- coding: utf-8 -*-

""" A simple and thin Python library for the Spotify Web API """

__all__ = ["Spotify", "SpotifyException"]

import json
import time
from .object_classes import (
    SpotiwiseAlbum,
    SpotiwiseArtist,
    SpotiwiseItem,
    SpotiwisePlayback,
    SpotiwisePlaylist,
    SpotiwiseTrack,
    SpotiwiseUser
)
import logging
import warnings

import requests
import urllib3
import six

from .exceptions import SpotifyException

logger = logging.getLogger(__name__)


class Spotify(object):
    """
        Example usage::

            import spotiwise

            urn = 'spotify:artist:3jOstUTkEu2JkjvRdBA5Gu'
            sp = spotiwise.Spotify()

            artist = sp.artist(urn)
            print(artist)

            user = sp.user('plamere')
            print(user)
    """
    max_retries = 3
    default_retry_codes = (429, 500, 502, 503, 504)
    country_codes = [
        "AD",
        "AR",
        "AU",
        "AT",
        "BE",
        "BO",
        "BR",
        "BG",
        "CA",
        "CL",
        "CO",
        "CR",
        "CY",
        "CZ",
        "DK",
        "DO",
        "EC",
        "SV",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "GT",
        "HN",
        "HK",
        "HU",
        "IS",
        "ID",
        "IE",
        "IT",
        "JP",
        "LV",
        "LI",
        "LT",
        "LU",
        "MY",
        "MT",
        "MX",
        "MC",
        "NL",
        "NZ",
        "NI",
        "NO",
        "PA",
        "PY",
        "PE",
        "PH",
        "PL",
        "PT",
        "SG",
        "ES",
        "SK",
        "SE",
        "CH",
        "TW",
        "TR",
        "GB",
        "US",
        "UY"]

    def __init__(
        self,
        auth=None,
        requests_session=True,
        client_credentials_manager=None,
        oauth_manager=None,
        auth_manager=None,
        proxies=None,
        requests_timeout=5,
        status_forcelist=None,
        retries=max_retries,
        status_retries=max_retries,
        backoff_factor=0.3,
        language=None,
        oauth=None
    ):
        """
        Creates a Spotify API client.

        :param auth: An authorization token (optional)
        :param requests_session:
            A Requests session object or a truthy value to create one.
            A falsy value disables sessions.
            It should generally be a good idea to keep sessions enabled
            for performance reasons (connection pooling).
        :param client_credentials_manager:
            SpotifyClientCredentials object
        :param oauth_manager:
            SpotifyOAuth object
        :param auth_manager:
            SpotifyOauth, SpotifyClientCredentials,
            or SpotifyImplicitGrant object
        :param proxies:
            Definition of proxies (optional).
            See Requests doc https://2.python-requests.org/en/master/user/advanced/#proxies
        :param requests_timeout:
            Tell Requests to stop waiting for a response after a given
            number of seconds
        :param status_forcelist:
            Tell requests what type of status codes retries should occur on
        :param retries:
            Total number of retries to allow
        :param status_retries:
            Number of times to retry on bad status codes
        :param backoff_factor:
            A backoff factor to apply between attempts after the second try
            See urllib3 https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html
        :param language:
            The language parameter advertises what language the user prefers to see.
            See ISO-639 language code: https://www.loc.gov/standards/iso639-2/php/code_list.php
        """
        self.prefix = "https://api.spotify.com/v1/"
        self._auth = auth
        self.client_credentials_manager = client_credentials_manager
        self.oauth_manager = oauth_manager
        self.auth_manager = auth_manager
        self.proxies = proxies
        self.requests_timeout = requests_timeout
        self.oauth = oauth
        self.status_forcelist = status_forcelist or self.default_retry_codes
        self.backoff_factor = backoff_factor
        self.retries = retries
        self.status_retries = status_retries
        self.language = language

        if isinstance(requests_session, requests.Session):
            self._session = requests_session
        else:
            if requests_session:  # Build a new session.
                self._build_session()
            else:  # Use the Requests API module as a "session".
                self._session = requests.api

    def set_auth(self, auth):
        self._auth = auth

    @property
    def auth_manager(self):
        return self._auth_manager

    @auth_manager.setter
    def auth_manager(self, auth_manager):
        if auth_manager is not None:
            self._auth_manager = auth_manager
        else:
            self._auth_manager = (
                self.client_credentials_manager or self.oauth_manager
            )

    def __del__(self):
        """Make sure the connection (pool) gets closed"""
        if isinstance(self._session, requests.Session):
            self._session.close()

    def _build_session(self):
        self._session = requests.Session()
        retry = urllib3.Retry(
            total=self.retries,
            connect=None,
            read=False,
            status=self.status_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.status_forcelist)

        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)

    def _auth_headers(self):
        if self._auth:
            return {"Authorization": "Bearer {0}".format(self._auth)}
        if not self.auth_manager:
            return {}
        try:
            token = self.auth_manager.get_access_token(as_dict=False)
        except TypeError:
            token = self.auth_manager.get_access_token()
        return {"Authorization": "Bearer {0}".format(token)}

    def _internal_call(self, method, url, payload, params):
        args = dict(params=params)
        if not url.startswith("http"):
            url = self.prefix + url
        headers = self._auth_headers()

        if "content_type" in args["params"]:
            headers["Content-Type"] = args["params"]["content_type"]
            del args["params"]["content_type"]
            if payload:
                args["data"] = payload
        else:
            headers["Content-Type"] = "application/json"
            if payload:
                args["data"] = json.dumps(payload)

        if self.language is not None:
            headers["Accept-Language"] = self.language

        logger.debug('Sending %s to %s with Headers: %s and Body: %r ',
                     method, url, headers, args.get('data'))

        try:
            response = self._session.request(
                method, url, headers=headers, proxies=self.proxies,
                timeout=self.requests_timeout, **args
            )

            response.raise_for_status()
            results = response.json()
        except requests.exceptions.HTTPError:
            try:
                msg = response.json()["error"]["message"]
            except (ValueError, KeyError):
                msg = "error"
            try:
                reason = response.json()["error"]["reason"]
            except (ValueError, KeyError):
                reason = None

            logger.error('HTTP Error for %s to %s returned %s due to %s',
                         method, url, response.status_code, msg)

            raise SpotifyException(
                response.status_code,
                -1,
                "%s:\n %s" % (response.url, msg),
                reason=reason,
                headers=response.headers,
            )
        except requests.exceptions.RetryError:
            logger.error('Max Retries reached')
            raise SpotifyException(
                599,
                -1,
                "%s:\n %s" % (response.url, "Max Retries"),
                headers=response.headers,
            )
        except ValueError:
            results = None

        logger.debug('RESULTS: %s', results)
        return results

    def _get(self, url, args=None, payload=None, **kwargs):
        if args:
            kwargs.update(args)

        return self._internal_call("GET", url, payload, kwargs)

    def _post(self, url, args=None, payload=None, **kwargs):
        if args:
            kwargs.update(args)
        return self._internal_call("POST", url, payload, kwargs)

    def _delete(self, url, args=None, payload=None, **kwargs):
        if args:
            kwargs.update(args)
        return self._internal_call("DELETE", url, payload, kwargs)

    def _put(self, url, args=None, payload=None, **kwargs):
        if args:
            kwargs.update(args)
        return self._internal_call("PUT", url, payload, kwargs)

    def next(self, result):
        """ returns the next result given a paged result

            Parameters:
                - result - a previously returned paged result
        """
        if result["next"]:
            return self._get(result["next"])
        else:
            return None

    def previous(self, result):
        """ returns the previous result given a paged result

            Parameters:
                - result - a previously returned paged result
        """
        if result["previous"]:
            return self._get(result["previous"])
        else:
            return None
                               
    def track(self, track_id):
        """ return a single track object given the track's ID, URI, or URL
        
            Parameters:
                - track_id - a spotify URI, URL or ID
        """
        return SpotiwiseTrack(**self._track(track_id))

    def _tracks(self, tracks, market=None):
        """ returns raw JSON for a list of tracks given a list of track IDs, URIs, or URLs

            Parameters:
                - tracks - a list of spotify URIs, URLs or IDs. Maximum: 50 IDs.
                - market - an ISO 3166-1 alpha-2 country code.
        """

        tlist = [self._get_id('track', t) for t in tracks]
        return self._get('tracks/?ids=' + ','.join(tlist), market = market)
    
    def tracks(self, tracks, market=None):
        """ returns a list of tracks given a list of track IDs, URIs, or URLs

            Parameters:
                - tracks - a list of spotify URIs, URLs or IDs
                - market - an ISO 3166-1 alpha-2 country code.
        """
        
        results = self._tracks(tracks, market).get('tracks')
        return [SpotiwiseTrack(**track) for track in results]

    def _artist(self, artist_id):
        """ returns raw JSON for a single artist given the artist's ID, URI or URL

            Parameters:
                - artist_id - an artist ID, URI or URL
        """

        trid = self._get_id('artist', artist_id)
        return self._get('artists/' + trid)
    
    def artist(self, artist_id):
        """ returns a single artist given the artist's ID, URI or URL

            Parameters:
                - artist_id - an artist ID, URI or URL
        """
        
        return SpotiwiseArtist(**self._artist(artist_id))

    def _artists(self, artists):
        """ returns a list of artists given the artist IDs, URIs, or URLs

            Parameters:
                - artists - a list of  artist IDs, URIs or URLs
        """

        tlist = [self._get_id('artist', a) for a in artists]
        return self._get('artists/?ids=' + ','.join(tlist))
    
    def artists(self, artists):
        """ returns a list of artists given the artist IDs, URIs, or URLs

            Parameters:
                - artists - a list of  artist IDs, URIs or URLs
        """
        
        results = self._artists(artists).get('artists')
        return [SpotiwiseArtist(**artist) for artist in results]


    # TODO: Migrate to Spotiwise object model
    def artist_albums(self, artist_id, album_type=None, country=None, limit=20,
                      offset=0):
        """ Get Spotify catalog information about an artist's albums

            Parameters:
                - artist_id - the artist ID, URI or URL
                - album_type - 'album', 'single', 'appears_on', 'compilation'
                - country - limit the response to one particular country.
                - limit  - the number of albums to return
                - offset - the index of the first album to return
        """

        trid = self._get_id("artist", artist_id)
        return self._get(
            "artists/" + trid + "/albums",
            album_type=album_type,
            country=country,
            limit=limit,
            offset=offset,
        )

    def _artist_top_tracks(self, artist_id, country='US'):
        """ Get raw JSON for Spotify catalog information about an artist's top 10 tracks
            by country.

            Parameters:
                - artist_id - the artist ID, URI or URL
                - country - limit the response to one particular country.
        """

        trid = self._get_id('artist', artist_id)
        return self._get('artists/' + trid + '/top-tracks', country=country)

    # TODO: Verify migration to Spotiwise object model
    def artist_top_tracks(self, artist_id, country='US'):
        """ Get Spotify catalog information about an artist's top 10 tracks
            by country.

            Parameters:
                - artist_id - the artist ID, URI or URL
                - country - limit the response to one particular country.
        """

        results = self._artist_top_tracks(artist_id, country).get('tracks')
        return [SpotiwiseTrack(**track) for track in results]

    def _artist_related_artists(self, artist_id):
        """ Get raw JSON for Spotify catalog information about artists similar to an
            identified artist. Similarity is based on analysis of the
            Spotify community's listening history.

            Parameters:
                - artist_id - the artist ID, URI or URL
        """
        trid = self._get_id('artist', artist_id)
        return self._get('artists/' + trid + '/related-artists')

    # TODO: Verify migration to Spotiwise object model
    def artist_related_artists(self, artist_id):
        """ Get Spotify catalog information about artists similar to an
            identified artist. Similarity is based on analysis of the
            Spotify community's listening history.

            Parameters:
                - artist_id - the artist ID, URI or URL
        """

        results = self._artist_related_artists(artists).get('artists')
        return [SpotiwiseArtist(**artist) for artist in results]

    def _album(self, album_id):
        """ returns raw JSON for a single album given the album's ID, URIs or URL

            Parameters:
                - album_id - the album ID, URI or URL
        """

        trid = self._get_id('album', album_id)
        return self._get('albums/' + trid)

    def album(self, album_id):
        """ returns a single album given the album's ID, URIs or URL

            Parameters:
                - album_id - the album ID, URI or URL
        """

        return SpotiwiseAlbum(**self._album(album_id))

    # TODO: Migrate to Spotiwise object model
    def album_tracks(self, album_id, limit=50, offset=0, market='US'):
        """ Get Spotify catalog information about an album's tracks

            Parameters:
                - album_id - the album ID, URI or URL
                - limit  - the number of items to return
                - offset - the index of the first item to return
                - market - an ISO 3166-1 alpha-2 country code.

        """

        trid = self._get_id("album", album_id)
        return self._get(
            "albums/" + trid + "/tracks/", limit=limit, offset=offset, market=market
        )

    def _albums(self, albums):
        """ returns raw JSON for a list of albums given the album IDs, URIs, or URLs

            Parameters:
                - albums - a list of  album IDs, URIs or URLs
        """

        tlist = [self._get_id('album', a) for a in albums]
        return self._get('albums/?ids=' + ','.join(tlist))

    def albums(self, albums):
        """ returns a list of albums given the album IDs, URIs, or URLs

            Parameters:
                - albums - a list of  album IDs, URIs or URLs
        """

        results = self._albums(albums).get('albums')
        return [SpotiwiseAlbum(**album) for album in results]

    def show(self, show_id, market=None):
        """ returns a single show given the show's ID, URIs or URL

            Parameters:
                - show_id - the show ID, URI or URL
                - market - an ISO 3166-1 alpha-2 country code.
                           The show must be available in the given market.
                           If user-based authorization is in use, the user's country
                           takes precedence. If neither market nor user country are
                           provided, the content is considered unavailable for the client.
        """

        trid = self._get_id("show", show_id)
        return self._get("shows/" + trid, market=market)

    def shows(self, shows, market=None):
        """ returns a list of shows given the show IDs, URIs, or URLs

            Parameters:
                - shows - a list of show IDs, URIs or URLs
                - market - an ISO 3166-1 alpha-2 country code.
                           Only shows available in the given market will be returned.
                           If user-based authorization is in use, the user's country
                           takes precedence. If neither market nor user country are
                           provided, the content is considered unavailable for the client.
        """

        tlist = [self._get_id("show", s) for s in shows]
        return self._get("shows/?ids=" + ",".join(tlist), market=market)

    def show_episodes(self, show_id, limit=50, offset=0, market=None):
        """ Get Spotify catalog information about a show's episodes

            Parameters:
                - show_id - the show ID, URI or URL
                - limit  - the number of items to return
                - offset - the index of the first item to return
                - market - an ISO 3166-1 alpha-2 country code.
                           Only episodes available in the given market will be returned.
                           If user-based authorization is in use, the user's country
                           takes precedence. If neither market nor user country are
                           provided, the content is considered unavailable for the client.
        """

        trid = self._get_id("show", show_id)
        return self._get(
            "shows/" + trid + "/episodes/", limit=limit, offset=offset, market=market
        )

    def episode(self, episode_id, market=None):
        """ returns a single episode given the episode's ID, URIs or URL

            Parameters:
                - episode_id - the episode ID, URI or URL
                - market - an ISO 3166-1 alpha-2 country code.
                           The episode must be available in the given market.
                           If user-based authorization is in use, the user's country
                           takes precedence. If neither market nor user country are
                           provided, the content is considered unavailable for the client.
        """

        trid = self._get_id("episode", episode_id)
        return self._get("episodes/" + trid, market=market)

    def episodes(self, episodes, market=None):
        """ returns a list of episodes given the episode IDs, URIs, or URLs

            Parameters:
                - episodes - a list of episode IDs, URIs or URLs
                - market - an ISO 3166-1 alpha-2 country code.
                           Only episodes available in the given market will be returned.
                           If user-based authorization is in use, the user's country
                           takes precedence. If neither market nor user country are
                           provided, the content is considered unavailable for the client.
        """

        tlist = [self._get_id("episode", e) for e in episodes]
        return self._get("episodes/?ids=" + ",".join(tlist), market=market)

    def search(self, q, limit=10, offset=0, type="track", market=None):
        """ searches for an item

            Parameters:
                - q - the search query (see how to write a query in the
                      official documentation https://developer.spotify.com/documentation/web-api/reference/search/search/)  # noqa
                - limit  - the number of items to return (min = 1, default = 10, max = 50)
                - offset - the index of the first item to return
                - type - the type of item to return. One of 'artist', 'album',
                         'track', 'playlist', 'show', or 'episode'
                - market - An ISO 3166-1 alpha-2 country code or the string
                           from_token.
        """
        return self._get(
            "search", q=q, limit=limit, offset=offset, type=type, market=market
        )

    def search_markets(self, q, limit=10, offset=0, type="track", markets=None, total=None):
        """ searches multple markets for an item

            Parameters:
                - q - the search query (see how to write a query in the
                      official documentation https://developer.spotify.com/documentation/web-api/reference/search/search/)  # noqa
                - limit  - the number of items to return (min = 1, default = 10, max = 50). If a search is to be done on multiple
                            markets, then this limit is applied to each market. (e.g. search US, CA, MX each with a limit of 10).
                - offset - the index of the first item to return
                - type - the type's of item's to return. One or more of 'artist', 'album',
                         'track', 'playlist', 'show', or 'episode'. If multiple types are desired, pass in a comma separated list.
                - markets - A list of ISO 3166-1 alpha-2 country codes. Search all country markets by default.
                - total - the total number of results to return if multiple markets are supplied in the search.
                          If multiple types are specified, this only applies to the first type.
        """
        if not markets:
            markets = self.country_codes

        if not (isinstance(markets, list) or isinstance(markets, tuple)):
            markets = []

        warnings.warn(
            "Searching multiple markets is poorly performing.",
            UserWarning,
        )
        return self._search_multiple_markets(q, limit, offset, type, markets, total)

    def _user(self, user):
        """ Gets raw JSON for basic profile information about a Spotify User

            Parameters:
                - user - the id of the usr
        """
        return self._get('users/' + user)

    def user(self, user):
        """ Gets basic profile information about a Spotify User

            Parameters:
                - user - the id of the usr
        """
        return SpotiwiseUser(**self._user(user))

    def _current_user_playlists(self, limit=50, offset=0):
        """ Get raw JSON for current user playlists without required getting his profile
            Parameters:
                - limit  - the number of items to return
                - offset - the index of the first item to return
        """
        return self._get("me/playlists", limit=limit, offset=offset)

    def current_user_playlists(self, limit=50, offset=0):
        """ Get current user playlists without required getting his profile
            Parameters:
                - limit  - the number of items to return
                - offset - the index of the first item to return
        """
        results = self._current_user_playlists(limit, offset).get('items')
        return [SpotiwisePlaylist(sp=self, **playlist) for playlist in results]

    def playlist_tracks(
        self,
        playlist_id,
        fields=None,
        limit=100,
        offset=0,
        market=None,
        additional_types=("track",)
    ):
        """ Get full details of the tracks of a playlist.

            Parameters:
                - playlist_id - the id of the playlist
                - fields - which fields to return
                - limit - the maximum number of tracks to return
                - offset - the index of the first track to return
                - market - an ISO 3166-1 alpha-2 country code.
                - additional_types - list of item types to return.
                                     valid types are: track and episode
        """
        warnings.warn(
            "You should use `playlist_items(playlist_id, ...,"
            "additional_types=('track',))` instead",
            DeprecationWarning,
        )
        return self.playlist_items(playlist_id, fields, limit, offset,
                                   market, additional_types)

    def playlist_items(
        self,
        playlist_id,
        fields=None,
        limit=100,
        offset=0,
        market=None,
        additional_types=("track", "episode")
    ):
        """ Get full details of the tracks and episodes of a playlist.

            Parameters:
                - playlist_id - the id of the playlist
                - fields - which fields to return
                - limit - the maximum number of tracks to return
                - offset - the index of the first track to return
                - market - an ISO 3166-1 alpha-2 country code.
                - additional_types - list of item types to return.
                                     valid types are: track and episode
        """
        plid = self._get_id("playlist", playlist_id)
        return self._get(
            "playlists/%s/tracks" % (plid),
            limit=limit,
            offset=offset,
            fields=fields,
            market=market,
            additional_types=",".join(additional_types)
        )

    def playlist_cover_image(self, playlist_id):
        """ Get cover of a playlist.

            Parameters:
                - playlist_id - the id of the playlist
        """
        plid = self._get_id("playlist", playlist_id)
        return self._get("playlists/%s/images" % (plid))

    def playlist_upload_cover_image(self, playlist_id, image_b64):
        """ Replace the image used to represent a specific playlist

            Parameters:
                - playlist_id - the id of the playlist
                - image_b64 - image data as a Base64 encoded JPEG image string
                    (maximum payload size is 256 KB)
        """
        plid = self._get_id("playlist", playlist_id)
        return self._put(
            "playlists/{}/images".format(plid),
            payload=image_b64,
            content_type="image/jpeg",
        )

    def user_playlist(self, user, playlist_id=None, fields=None, market=None):
        warnings.warn(
            "You should use `playlist(playlist_id)` instead",
            DeprecationWarning,
        )

    def _user_playlist(self, user, playlist_id=None, fields=None):
        """ Gets playlist of a user

            Parameters:
                - user - the id of the user
                - playlist_id - the id of the playlist
                - fields - which fields to return
        """
        if playlist_id is None:
            return self._get("users/%s/starred" % (user), fields=fields)
        plid = self._get_id('playlist', playlist_id)
        return self._get("users/%s/playlists/%s" % (user, plid), fields=fields)

    def user_playlist(self, user, playlist_id=None, fields=None, precache=False):
        """ Gets playlist of a user
            Parameters:
                - user - the id of the user
                - playlist_id - the id of the playlist
                - fields - which fields to return
        """

        return SpotiwisePlaylist(**self._user_playlist(user, playlist_id, fields), sp=self, precache=precache)

    # TODO: Determine if candidate to migrate to Spotiwise object model or for deprecation
    def user_playlist_tracks(self, user, playlist_id=None, fields=None,
                             limit=100, offset=0, market=None):
        """ Get full details of the tracks of a playlist owned by a user.

            Parameters:
                - user - the id of the user
                - playlist_id - the id of the playlist
                - fields - which fields to return
                - limit - the maximum number of tracks to return
                - offset - the index of the first track to return
                - market - an ISO 3166-1 alpha-2 country code.
        """
        return self.playlist_tracks(
            playlist_id,
            limit=limit,
            offset=offset,
            fields=fields,
            market=market,
        )

    def _user_playlists(self, user, limit=50, offset=0):
        """ Gets playlists of a user

            Parameters:
                - user - the id of the usr
                - limit  - the number of items to return
                - offset - the index of the first item to return
        """
        return self._get(
            "users/%s/playlists" % user, limit=limit, offset=offset
        )

    def user_playlists(self, user, limit=50, offset=0):
        """ Gets playlists of a user

            Parameters:
                - user - the id of the usr
                - limit  - the number of items to return
                - offset - the index of the first item to return
        """

        results = self._user_playlists(limit, offset).get('items')
        return [SpotiwisePlaylist(sp=self, **playlist) for playlist in results]

    def user_playlist_create(self, user, name, public=True, collaborative=False, description=""):
        """ Creates a playlist for a user

            Parameters:
                - user - the id of the user
                - name - the name of the playlist
                - public - is the created playlist public
                - collaborative - is the created playlist collaborative
                - description - the description of the playlist
        """
        data = {
            "name": name,
            "public": public,
            "collaborative": collaborative,
            "description": description
        }

        return self._post("users/%s/playlists" % (user,), payload=data)

    def user_playlist_change_details(
        self,
        user,
        playlist_id,
        name=None,
        public=None,
        collaborative=None,
        description=None,
    ):
        warnings.warn(
            "You should use `playlist_change_details(playlist_id, ...)` instead",
            DeprecationWarning,
        )
        """ Changes a playlist's name and/or public/private state

            Parameters:
                - user - the id of the user
                - playlist_id - the id of the playlist
                - name - optional name of the playlist
                - public - optional is the playlist public
                - collaborative - optional is the playlist collaborative
                - description - optional description of the playlist
        """

        return self.playlist_change_details(playlist_id, name, public,
                                            collaborative, description)

    def user_playlist_unfollow(self, user, playlist_id):
        """ Unfollows (deletes) a playlist for a user

            Parameters:
                - user - the id of the user
                - name - the name of the playlist
        """
        warnings.warn(
            "You should use `current_user_unfollow_playlist(playlist_id)` instead",
            DeprecationWarning,
        )
        return self.current_user_unfollow_playlist(playlist_id)

    def user_playlist_add_tracks(
        self, user, playlist_id, tracks, position=None
    ):
        warnings.warn(
            "You should use `playlist_add_items(playlist_id, tracks)` instead",
            DeprecationWarning,
        )
        """ Adds tracks to a playlist

            Parameters:
                - user - the id of the user
                - playlist_id - the id of the playlist
                - tracks - a list of track URIs, URLs or IDs
                - position - the position to add the tracks
        """
        return self.playlist_add_items(playlist_id, tracks, position)

    def user_playlist_replace_tracks(self, user, playlist_id, tracks):
        """ Replace all tracks in a playlist

            Parameters:
                - user - the id of the user
                - playlist_id - the id of the playlist
                - tracks - the list of track ids to add to the playlist
        """
        warnings.warn(
            "You should use `playlist_replace_items(playlist_id, tracks)` instead",
            DeprecationWarning,
        )
        return self.playlist_replace_items(playlist_id, tracks)

    def user_playlist_reorder_tracks(
        self,
        user,
        playlist_id,
        range_start,
        insert_before,
        range_length=1,
        snapshot_id=None,
    ):
        """ Reorder tracks in a playlist

            Parameters:
                - user - the id of the user
                - playlist_id - the id of the playlist
                - range_start - the position of the first track to be reordered
                - range_length - optional the number of tracks to be reordered
                                 (default: 1)
                - insert_before - the position where the tracks should be
                                  inserted
                - snapshot_id - optional playlist's snapshot ID
        """
        warnings.warn(
            "You should use `playlist_reorder_items(playlist_id, ...)` instead",
            DeprecationWarning,
        )
        return self.playlist_reorder_items(playlist_id, range_start,
                                           range_length, insert_before,
                                           snapshot_id)

    def user_playlist_remove_all_occurrences_of_tracks(
        self, user, playlist_id, tracks, snapshot_id=None
    ):
        """ Removes all occurrences of the given tracks from the given playlist

            Parameters:
                - user - the id of the user
                - playlist_id - the id of the playlist
                - tracks - the list of track ids to remove from the playlist
                - snapshot_id - optional id of the playlist snapshot

        """
        warnings.warn(
            "You should use `playlist_remove_all_occurrences_of_items"
            "(playlist_id, tracks)` instead",
            DeprecationWarning,
        )
        return self.playlist_remove_all_occurrences_of_items(playlist_id,
                                                             tracks,
                                                             snapshot_id)

    def user_playlist_remove_specific_occurrences_of_tracks(
        self, user, playlist_id, tracks, snapshot_id=None
    ):
        """ Removes all occurrences of the given tracks from the given playlist

            Parameters:
                - user - the id of the user
                - playlist_id - the id of the playlist
                - tracks - an array of objects containing Spotify URIs of the
                    tracks to remove with their current positions in the
                    playlist.  For example:
                        [  { "uri":"4iV5W9uYEdYUVa79Axb7Rh", "positions":[2] },
                        { "uri":"1301WleyT98MSxVHPZCA6M", "positions":[7] } ]
                - snapshot_id - optional id of the playlist snapshot
        """
        warnings.warn(
            "You should use `playlist_remove_specific_occurrences_of_items"
            "(playlist_id, tracks)` instead",
            DeprecationWarning,
        )
        plid = self._get_id("playlist", playlist_id)
        ftracks = []
        for tr in tracks:
            ftracks.append(
                {
                    "uri": self._get_uri("track", tr["uri"]),
                    "positions": tr["positions"],
                }
            )
        payload = {"tracks": ftracks}
        if snapshot_id:
            payload["snapshot_id"] = snapshot_id
        return self._delete(
            "users/%s/playlists/%s/tracks" % (user, plid), payload=payload
        )

    def user_playlist_follow_playlist(self, playlist_owner_id, playlist_id):
        """
        Add the current authenticated user as a follower of a playlist.

        Parameters:
            - playlist_owner_id - the user id of the playlist owner
            - playlist_id - the id of the playlist

        """
        warnings.warn(
            "You should use `current_user_follow_playlist(playlist_id)` instead",
            DeprecationWarning,
        )
        return self.current_user_follow_playlist(playlist_id)

    def user_playlist_is_following(
        self, playlist_owner_id, playlist_id, user_ids
    ):
        """
        Check to see if the given users are following the given playlist

        Parameters:
            - playlist_owner_id - the user id of the playlist owner
            - playlist_id - the id of the playlist
            - user_ids - the ids of the users that you want to check to see
                if they follow the playlist. Maximum: 5 ids.

        """
        warnings.warn(
            "You should use `playlist_is_following(playlist_id, user_ids)` instead",
            DeprecationWarning,
        )
        return self.playlist_is_following(playlist_id, user_ids)

    def playlist_change_details(
        self,
        playlist_id,
        name=None,
        public=None,
        collaborative=None,
        description=None,
    ):
        """ Changes a playlist's name and/or public/private state

            Parameters:
                - playlist_id - the id of the playlist
                - name - optional name of the playlist
                - public - optional is the playlist public
                - collaborative - optional is the playlist collaborative
                - description - optional description of the playlist
        """

        data = {}
        if isinstance(name, six.string_types):
            data["name"] = name
        if isinstance(public, bool):
            data["public"] = public
        if isinstance(collaborative, bool):
            data["collaborative"] = collaborative
        if isinstance(description, six.string_types):
            data["description"] = description
        return self._put(
            "playlists/%s" % (playlist_id), payload=data
        )

    def current_user_unfollow_playlist(self, playlist_id):
        """ Unfollows (deletes) a playlist for the current authenticated
            user

            Parameters:
                - name - the name of the playlist
        """
        return self._delete(
            "playlists/%s/followers" % (playlist_id)
        )

    def playlist_add_items(
        self, playlist_id, items, position=None
    ):
        """ Adds tracks/episodes to a playlist

            Parameters:
                - playlist_id - the id of the playlist
                - items - a list of track/episode URIs, URLs or IDs
                - position - the position to add the tracks
        """
        plid = self._get_id("playlist", playlist_id)
        ftracks = [self._get_uri("track", tid) for tid in items]
        return self._post(
            "playlists/%s/tracks" % (plid),
            payload=ftracks,
            position=position,
        )

    def playlist_replace_items(self, playlist_id, items):
        """ Replace all tracks/episodes in a playlist

            Parameters:
                - playlist_id - the id of the playlist
                - items - list of track/episode ids to comprise playlist
        """
        plid = self._get_id("playlist", playlist_id)
        ftracks = [self._get_uri("track", tid) for tid in items]
        payload = {"uris": ftracks}
        return self._put(
            "playlists/%s/tracks" % (plid), payload=payload
        )

    def playlist_reorder_items(
        self,
        playlist_id,
        range_start,
        insert_before,
        range_length=1,
        snapshot_id=None,
    ):
        """ Reorder tracks in a playlist

            Parameters:
                - playlist_id - the id of the playlist
                - range_start - the position of the first track to be reordered
                - range_length - optional the number of tracks to be reordered
                                 (default: 1)
                - insert_before - the position where the tracks should be
                                  inserted
                - snapshot_id - optional playlist's snapshot ID
        """
        plid = self._get_id("playlist", playlist_id)
        payload = {
            "range_start": range_start,
            "range_length": range_length,
            "insert_before": insert_before,
        }
        if snapshot_id:
            payload["snapshot_id"] = snapshot_id
        return self._put(
            "playlists/%s/tracks" % (plid), payload=payload
        )

    def playlist_remove_all_occurrences_of_items(
        self, playlist_id, items, snapshot_id=None
    ):
        """ Removes all occurrences of the given tracks from the given playlist

            Parameters:
                - playlist_id - the id of the playlist
                - items - list of track/episode ids to remove from the playlist
                - snapshot_id - optional id of the playlist snapshot

        """

        plid = self._get_id("playlist", playlist_id)
        ftracks = [self._get_uri("track", tid) for tid in items]
        payload = {"tracks": [{"uri": track} for track in ftracks]}
        if snapshot_id:
            payload["snapshot_id"] = snapshot_id
        return self._delete(
            "playlists/%s/tracks" % (plid), payload=payload
        )

    def playlist_remove_specific_occurrences_of_items(
        self, playlist_id, items, snapshot_id=None
    ):
        """ Removes all occurrences of the given tracks from the given playlist

            Parameters:
                - playlist_id - the id of the playlist
                - items - an array of objects containing Spotify URIs of the
                    tracks/episodes to remove with their current positions in
                    the playlist.  For example:
                        [  { "uri":"4iV5W9uYEdYUVa79Axb7Rh", "positions":[2] },
                        { "uri":"1301WleyT98MSxVHPZCA6M", "positions":[7] } ]
                - snapshot_id - optional id of the playlist snapshot
        """

        plid = self._get_id("playlist", playlist_id)
        ftracks = []
        for tr in items:
            ftracks.append(
                {
                    "uri": self._get_uri("track", tr["uri"]),
                    "positions": tr["positions"],
                }
            )
        payload = {"tracks": ftracks}
        if snapshot_id:
            payload["snapshot_id"] = snapshot_id
        return self._delete(
            "playlists/%s/tracks" % (plid), payload=payload
        )

    def current_user_follow_playlist(self, playlist_id):
        """
        Add the current authenticated user as a follower of a playlist.

        Parameters:
            - playlist_id - the id of the playlist

        """
        return self._put(
            "playlists/{}/followers".format(playlist_id)
        )

    def playlist_is_following(
        self, playlist_id, user_ids
    ):
        """
        Check to see if the given users are following the given playlist

        Parameters:
            - playlist_id - the id of the playlist
            - user_ids - the ids of the users that you want to check to see
                if they follow the playlist. Maximum: 5 ids.

        """
        endpoint = "playlists/{}/followers/contains?ids={}"
        return self._get(
            endpoint.format(playlist_id, ",".join(user_ids))
        )

    # TODO: Migrate to Spotiwise object model
    def me(self):
        """ Get detailed profile information about the current user.
            An alias for the 'current_user' method.
        """
        return self._get("me/")

    # TODO: Determine if candidate to migrate to Spotiwise object model or for deprecation
    def current_user(self):
        """ Get detailed profile information about the current user.
            An alias for the 'me' method.
        """
        return self.me()

    # TODO: Migrate to Spotiwise object model
    def current_user_playing_track(self):
        ''' Get information about the current users currently playing track.
        '''
        return self._get('me/player/currently-playing')

    # TODO: Migrate to Spotiwise object model
    def current_user_saved_albums(self, limit=20, offset=0):
        """ Gets a list of the albums saved in the current authorized user's
            "Your Music" library

            Parameters:
                - limit - the number of albums to return
                - offset - the index of the first album to return

        """
        return self._get("me/player/currently-playing")

    # TODO: Migrate to Spotiwise object model
    def current_user_saved_tracks(self, limit=20, offset=0):
        """ Gets a list of the tracks saved in the current authorized user's
            "Your Music" library

            Parameters:
                - limit - the number of tracks to return
                - offset - the index of the first track to return

        """
        return self._get("me/tracks", limit=limit, offset=offset)

    # TODO: Migrate to Spotiwise object model
    def current_user_followed_artists(self, limit=20, after=None):
        """ Gets a list of the artists followed by the current authorized user

            Parameters:
                - limit - the number of artists to return
                - after - the last artist ID retrieved from the previous
                          request

        """
        return self._get(
            "me/following", type="artist", limit=limit, after=after
        )

    def current_user_following_artists(self, ids=None):
        """ Check if the current user is following certain artists

            Returns list of booleans respective to ids

            Parameters:
                - ids - a list of artist URIs, URLs or IDs
        """
        idlist = []
        if ids is not None:
            idlist = [self._get_id("artist", i) for i in ids]
        return self._get(
            "me/following/contains", ids=",".join(idlist), type="artist"
        )

    def current_user_following_users(self, ids=None):
        """ Check if the current user is following certain artists

            Returns list of booleans respective to ids

            Parameters:
                - ids - a list of user URIs, URLs or IDs
        """
        idlist = []
        if ids is not None:
            idlist = [self._get_id("user", i) for i in ids]
        return self._get(
            "me/following/contains", ids=",".join(idlist), type="user"
        )

    def current_user_saved_tracks_delete(self, tracks=None):
        """ Remove one or more tracks from the current user's
            "Your Music" library.

            Parameters:
                - tracks - a list of track URIs, URLs or IDs
        """
        tlist = []
        if tracks is not None:
            tlist = [self._get_id("track", t) for t in tracks]
        return self._delete("me/tracks/?ids=" + ",".join(tlist))

    def current_user_saved_tracks_contains(self, tracks=None):
        """ Check if one or more tracks is already saved in
            the current Spotify user’s “Your Music” library.

            Parameters:
                - tracks - a list of track URIs, URLs or IDs
        """
        tlist = []
        if tracks is not None:
            tlist = [self._get_id("track", t) for t in tracks]
        return self._get("me/tracks/contains?ids=" + ",".join(tlist))

    def current_user_saved_tracks_add(self, tracks=None):
        """ Add one or more tracks to the current user's
            "Your Music" library.

            Parameters:
                - tracks - a list of track URIs, URLs or IDs
        """
        tlist = []
        if tracks is not None:
            tlist = [self._get_id("track", t) for t in tracks]
        return self._put("me/tracks/?ids=" + ",".join(tlist))

    def current_user_top_artists(
        self, limit=20, offset=0, time_range="medium_term"
    ):
        """ Get the current user's top artists

            Parameters:
                - limit - the number of entities to return
                - offset - the index of the first entity to return
                - time_range - Over what time frame are the affinities computed
                  Valid-values: short_term, medium_term, long_term
        """
        return self._get(
            "me/top/artists", time_range=time_range, limit=limit, offset=offset
        )

    def current_user_top_tracks(
        self, limit=20, offset=0, time_range="medium_term"
    ):
        """ Get the current user's top tracks

            Parameters:
                - limit - the number of entities to return
                - offset - the index of the first entity to return
                - time_range - Over what time frame are the affinities computed
                  Valid-values: short_term, medium_term, long_term
        """
        return self._get(
            "me/top/tracks", time_range=time_range, limit=limit, offset=offset
        )

    # TODO: Migrate to Spotiwise object model
    def current_user_recently_played(self, limit=50):
        """ Get the current user's recently played tracks

            Parameters:
                - limit - the number of entities to return
                - after - unix timestamp in milliseconds. Returns all items
                          after (but not including) this cursor position.
                          Cannot be used if before is specified.
                - before - unix timestamp in milliseconds. Returns all items
                           before (but not including) this cursor position.
                           Cannot be used if after is specified
        """
        return self._get(
            "me/player/recently-played",
            limit=limit,
            after=after,
            before=before,
        )

    def current_user_saved_albums_contains(self, albums=[]):
        """ Check if one or more albums is already saved in
            the current Spotify user’s “Your Music” library.

            Parameters:
                - albums - a list of album URIs, URLs or IDs
        """
        alist = [self._get_id("album", a) for a in albums]
        return self._get("me/albums/contains?ids=" + ",".join(alist))

    def current_user_saved_albums_add(self, albums=[]):
        """ Add one or more albums to the current user's
            "Your Music" library.
            Parameters:
                - albums - a list of album URIs, URLs or IDs
        """
        alist = [self._get_id("album", a) for a in albums]
        return self._put("me/albums?ids=" + ",".join(alist))

    def current_user_saved_albums_delete(self, albums=[]):
        """ Remove one or more albums from the current user's
            "Your Music" library.

            Parameters:
                - albums - a list of album URIs, URLs or IDs
        """
        alist = [self._get_id("album", a) for a in albums]
        return self._delete("me/albums/?ids=" + ",".join(alist))

    def current_user_saved_shows(self, limit=50, offset=0):
        """ Gets a list of the shows saved in the current authorized user's
            "Your Music" library

            Parameters:
                - limit - the number of shows to return
                - offset - the index of the first show to return

        """
        return self._get("me/shows", limit=limit, offset=offset)

    def current_user_saved_shows_contains(self, shows=[]):
        """ Check if one or more shows is already saved in
            the current Spotify user’s “Your Music” library.

            Parameters:
                - shows - a list of show URIs, URLs or IDs
        """
        slist = [self._get_id("show", s) for s in shows]
        return self._get("me/shows/contains?ids=" + ",".join(slist))

    def current_user_saved_shows_add(self, shows=[]):
        """ Add one or more albums to the current user's
            "Your Music" library.
            Parameters:
                - shows - a list of show URIs, URLs or IDs
        """
        slist = [self._get_id("show", s) for s in shows]
        return self._put("me/shows?ids=" + ",".join(slist))

    def current_user_saved_shows_delete(self, shows=[]):
        """ Remove one or more shows from the current user's
            "Your Music" library.

            Parameters:
                - shows - a list of show URIs, URLs or IDs
        """
        slist = [self._get_id("show", s) for s in shows]
        return self._delete("me/shows/?ids=" + ",".join(slist))

    def user_follow_artists(self, ids=[]):
        """ Follow one or more artists
            Parameters:
                - ids - a list of artist IDs
        """
        return self._put("me/following?type=artist&ids=" + ",".join(ids))

    def user_follow_users(self, ids=[]):
        """ Follow one or more users
            Parameters:
                - ids - a list of user IDs
        """
        return self._put("me/following?type=user&ids=" + ",".join(ids))

    def user_unfollow_artists(self, ids=[]):
        """ Unfollow one or more artists
            Parameters:
                - ids - a list of artist IDs
        """
        return self._delete("me/following?type=artist&ids=" + ",".join(ids))

    def user_unfollow_users(self, ids=[]):
        """ Unfollow one or more users
            Parameters:
                - ids - a list of user IDs
        """
        return self._delete("me/following?type=user&ids=" + ",".join(ids))

    # TODO: Migrate to Spotiwise object model
    def featured_playlists(self, locale=None, country=None, timestamp=None,
                           limit=20, offset=0):
        """ Get a list of Spotify featured playlists

            Parameters:
                - locale - The desired language, consisting of a lowercase ISO
                  639 language code and an uppercase ISO 3166-1 alpha-2 country
                  code, joined by an underscore.

                - country - An ISO 3166-1 alpha-2 country code.

                - timestamp - A timestamp in ISO 8601 format:
                  yyyy-MM-ddTHH:mm:ss. Use this parameter to specify the user's
                  local time to get results tailored for that specific date and
                  time in the day

                - limit - The maximum number of items to return. Default: 20.
                  Minimum: 1. Maximum: 50

                - offset - The index of the first item to return. Default: 0
                  (the first object). Use with limit to get the next set of
                  items.
        """
        return self._get(
            "browse/featured-playlists",
            locale=locale,
            country=country,
            timestamp=timestamp,
            limit=limit,
            offset=offset,
        )

    # TODO: Migrate to Spotiwise object model
    def new_releases(self, country=None, limit=20, offset=0):
        """ Get a list of new album releases featured in Spotify

            Parameters:
                - country - An ISO 3166-1 alpha-2 country code.

                - limit - The maximum number of items to return. Default: 20.
                  Minimum: 1. Maximum: 50

                - offset - The index of the first item to return. Default: 0
                  (the first object). Use with limit to get the next set of
                  items.
        """
        return self._get(
            "browse/new-releases", country=country, limit=limit, offset=offset
        )

    # TODO: Migrate to Spotiwise object model??
    def categories(self, country=None, locale=None, limit=20, offset=0):
        """ Get a list of new album releases featured in Spotify

            Parameters:
                - country - An ISO 3166-1 alpha-2 country code.
                - locale - The desired language, consisting of an ISO 639
                  language code and an ISO 3166-1 alpha-2 country code, joined
                  by an underscore.

                - limit - The maximum number of items to return. Default: 20.
                  Minimum: 1. Maximum: 50

                - offset - The index of the first item to return. Default: 0
                  (the first object). Use with limit to get the next set of
                  items.
        """
        return self._get('browse/categories', country=country, locale=locale,
                         limit=limit, offset=offset)

    # TODO: Migrate to Spotiwise object model??
    def category_playlists(self, category_id=None, country=None, limit=20,
                           offset=0):
        """ Get a list of new album releases featured in Spotify

            Parameters:
                - category_id - The Spotify category ID for the category.

                - country - An ISO 3166-1 alpha-2 country code.

                - limit - The maximum number of items to return. Default: 20.
                  Minimum: 1. Maximum: 50

                - offset - The index of the first item to return. Default: 0
                  (the first object). Use with limit to get the next set of
                  items.
        """
        return self._get('browse/categories/' + category_id + '/playlists',
                         country=country, limit=limit, offset=offset)

    # TODO: Migrate to Spotiwise object model??
    def recommendations(self, seed_artists=None, seed_genres=None,
                        seed_tracks=None, limit=20, country=None, **kwargs):
        """ Get a list of recommended tracks for one to five seeds.
            (at least one of `seed_artists`, `seed_tracks` and `seed_genres`
            are needed)

            Parameters:
                - seed_artists - a list of artist IDs, URIs or URLs
                - seed_tracks - a list of track IDs, URIs or URLs
                - seed_genres - a list of genre names. Available genres for
                                recommendations can be found by calling
                                recommendation_genre_seeds

                - country - An ISO 3166-1 alpha-2 country code. If provided,
                            all results will be playable in this country.

                - limit - The maximum number of items to return. Default: 20.
                          Minimum: 1. Maximum: 100

                - min/max/target_<attribute> - For the tuneable track
                    attributes listed in the documentation, these values
                    provide filters and targeting on results.
        """
        params = dict(limit=limit)
        if seed_artists:
            params["seed_artists"] = ",".join(
                [self._get_id("artist", a) for a in seed_artists]
            )
        if seed_genres:
            params["seed_genres"] = ",".join(seed_genres)
        if seed_tracks:
            params["seed_tracks"] = ",".join(
                [self._get_id("track", t) for t in seed_tracks]
            )
        if country:
            params["market"] = country

        for attribute in [
            "acousticness",
            "danceability",
            "duration_ms",
            "energy",
            "instrumentalness",
            "key",
            "liveness",
            "loudness",
            "mode",
            "popularity",
            "speechiness",
            "tempo",
            "time_signature",
            "valence",
        ]:
            for prefix in ["min_", "max_", "target_"]:
                param = prefix + attribute
                if param in kwargs:
                    params[param] = kwargs[param]
        return self._get("recommendations", **params)

    def recommendation_genre_seeds(self):
        """ Get a list of genres available for the recommendations function.
        """
        return self._get("recommendations/available-genre-seeds")

    def audio_features(self, tracks=[]):
        """ Get audio features for one or multiple tracks based upon their Spotify IDs
            Parameters:
                - tracks - a list of track URIs, URLs or IDs, maximum: 100 ids
        """
        if isinstance(tracks, str):
            trackid = self._get_id("track", tracks)
            results = self._get("audio-features/?ids=" + trackid)
        else:
            tlist = [self._get_id("track", t) for t in tracks]
            results = self._get("audio-features/?ids=" + ",".join(tlist))
        # the response has changed, look for the new style first, and if
        # its not there, fallback on the old style
        if "audio_features" in results:
            return results["audio_features"]
        else:
            return results

    def audio_analysis(self, id):
        """ Get audio analysis for a track based upon its Spotify ID
            Parameters:
                - id - a track URIs, URLs or IDs
        """
        id = self._get_id('track', id)
        return self._get('audio-analysis/'+id)

    # TODO: Migrate to Spotiwise object model
    def devices(self):
        """ Get a list of user's available devices.
        """
        return self._get("me/player/devices")

    # TODO: Migrate to Spotiwise object model
    def current_playback(self, market=None):
        """ Get information about user's current playback.

            Parameters:
                - market - an ISO 3166-1 alpha-2 country code.
        """
        return self._get("me/player", market=market)

    # TODO: Migrate to Spotiwise object model
    def currently_playing(self, market=None):
        """ Get user's currently playing track.

            Parameters:
                - market - an ISO 3166-1 alpha-2 country code.
        """
        return self._get("me/player/currently-playing", market=market)

    def transfer_playback(self, device_id, force_play=True):
        """ Transfer playback to another device.
            Note that the API accepts a list of device ids, but only
            actually supports one.

            Parameters:
                - device_id - transfer playback to this device
                - force_play - true: after transfer, play. false:
                               keep current state.
        """
        data = {"device_ids": [device_id], "play": force_play}
        return self._put("me/player", payload=data)

    def start_playback(
        self, device_id=None, context_uri=None, uris=None, offset=None, position_ms=None
    ):
        """ Start or resume user's playback.

            Provide a `context_uri` to start playback or a album,
            artist, or playlist.

            Provide a `uris` list to start playback of one or more
            tracks.

            Provide `offset` as {"position": <int>} or {"uri": "<track uri>"}
            to start playback at a particular offset.

            Parameters:
                - device_id - device target for playback
                - context_uri - spotify context uri to play
                - uris - spotify track uris
                - offset - offset into context by index or track
                - position_ms - (optional) indicates from what position to start playback.
                                Must be a positive number. Passing in a position that is
                                greater than the length of the track will cause the player to
                                start playing the next song.
        """
        if context_uri is not None and uris is not None:
            logger.warning("Specify either context uri or uris, not both")
            return
        if uris is not None and not isinstance(uris, list):
            logger.warning("URIs must be a list")
            return
        data = {}
        if context_uri is not None:
            data["context_uri"] = context_uri
        if uris is not None:
            data["uris"] = uris
        if offset is not None:
            data["offset"] = offset
        if position_ms is not None:
            data["position_ms"] = position_ms
        return self._put(
            self._append_device_id("me/player/play", device_id), payload=data
        )

    def pause_playback(self, device_id=None):
        """ Pause user's playback.

            Parameters:
                - device_id - device target for playback
        """
        return self._put(self._append_device_id("me/player/pause", device_id))

    def next_track(self, device_id=None):
        """ Skip user's playback to next track.

            Parameters:
                - device_id - device target for playback
        """
        return self._post(self._append_device_id("me/player/next", device_id))

    def previous_track(self, device_id=None):
        """ Skip user's playback to previous track.

            Parameters:
                - device_id - device target for playback
        """
        return self._post(
            self._append_device_id("me/player/previous", device_id)
        )

    def seek_track(self, position_ms, device_id=None):
        """ Seek to position in current track.

            Parameters:
                - position_ms - position in milliseconds to seek to
                - device_id - device target for playback
        """
        if not isinstance(position_ms, int):
            logger.warning("Position_ms must be an integer")
            return
        return self._put(
            self._append_device_id(
                "me/player/seek?position_ms=%s" % position_ms, device_id
            )
        )

    def repeat(self, state, device_id=None):
        """ Set repeat mode for playback.

            Parameters:
                - state - `track`, `context`, or `off`
                - device_id - device target for playback
        """
        if state not in ["track", "context", "off"]:
            logger.warning("Invalid state")
            return
        self._put(
            self._append_device_id(
                "me/player/repeat?state=%s" % state, device_id
            )
        )

    def volume(self, volume_percent, device_id=None):
        """ Set playback volume.

            Parameters:
                - volume_percent - volume between 0 and 100
                - device_id - device target for playback
        """
        if not isinstance(volume_percent, int):
            logger.warning("Volume must be an integer")
            return
        if volume_percent < 0 or volume_percent > 100:
            logger.warning("Volume must be between 0 and 100, inclusive")
            return
        self._put(
            self._append_device_id(
                "me/player/volume?volume_percent=%s" % volume_percent,
                device_id,
            )
        )

    def shuffle(self, state, device_id=None):
        """ Toggle playback shuffling.

            Parameters:
                - state - true or false
                - device_id - device target for playback
        """
        if not isinstance(state, bool):
            logger.warning("state must be a boolean")
            return
        state = str(state).lower()
        self._put(
            self._append_device_id(
                "me/player/shuffle?state=%s" % state, device_id
            )
        )

    def add_to_queue(self, uri, device_id=None):
        """ Adds a song to the end of a user's queue

            If device A is currently playing music and you try to add to the queue
            and pass in the id for device B, you will get a
            'Player command failed: Restriction violated' error
            I therefore reccomend leaving device_id as None so that the active device is targeted

            :param uri: song uri, id, or url
            :param device_id:
                the id of a Spotify device.
                If None, then the active device is used.

        """

        uri = self._get_uri("track", uri)

        endpoint = "me/player/queue?uri=%s" % uri

        if device_id is not None:
            endpoint += "&device_id=%s" % device_id

        return self._post(endpoint)

    def _append_device_id(self, path, device_id):
        """ Append device ID to API path.

            Parameters:
                - device_id - device id to append
        """
        if device_id:
            if "?" in path:
                path += "&device_id=%s" % device_id
            else:
                path += "?device_id=%s" % device_id
        return path

    def _get_id(self, type, id):
        fields = id.split(":")
        if len(fields) >= 3:
            if type != fields[-2]:
                logger.warning('Expected id of type %s but found type %s %s',
                               type, fields[-2], id)
            return fields[-1]
        fields = id.split("/")
        if len(fields) >= 3:
            itype = fields[-2]
            if type != itype:
                logger.warning('Expected id of type %s but found type %s %s',
                               type, itype, id)
            return fields[-1].split("?")[0]
        return id

    def _get_uri(self, type, id):
        return "spotify:" + type + ":" + self._get_id(type, id)

    def _search_multiple_markets(self, q, limit, offset, type, markets, total):
        if total and limit > total:
            limit = total
            warnings.warn(
                "limit was auto-adjusted to equal {} as it must not be higher than total".format(
                    total),
                UserWarning,
            )

        results = {}
        first_type = type.split(",")[0] + 's'
        count = 0

        for country in markets:
            result = self._get(
                "search", q=q, limit=limit, offset=offset, type=type, market=country
            )
            results[country] = result

            count += len(result[first_type]['items'])
            if total and count >= total:
                break
            if total and limit > total - count:
                # when approaching `total` results, adjust `limit` to not request more
                # items than needed
                limit = total - count

        return results
