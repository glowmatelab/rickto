import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from Elevenyts import config

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=config.SPOTIFY_CLIENT_ID,
    client_secret=config.SPOTIFY_CLIENT_SECRET,
))

SPOTIFY_REGEX = re.compile(
    r"https?://open\.spotify\.com/(track|playlist|album)/([A-Za-z0-9]+)"
)

def is_spotify(url: str) -> bool:
    return bool(SPOTIFY_REGEX.match(url))

async def get_track(url: str) -> str | None:
    try:
        match = SPOTIFY_REGEX.match(url)
        if not match:
            return None

        sp_type = match.group(1)
        sp_id = match.group(2)

        if sp_type == "track":
            # sp.track() ki jagah sp.search() use karo
            results = sp.search(q=f"spotify:track:{sp_id}", type="track", limit=1)
            items = results["tracks"]["items"]
            if not items:
                return None
            title = items[0]["name"]
            artist = items[0]["artists"][0]["name"]
            return f"{title} {artist}"

        return None
    except Exception:
        return None

async def get_playlist(url: str) -> list[str]:
    try:
        match = SPOTIFY_REGEX.match(url)
        if not match:
            return []

        sp_type = match.group(1)
        sp_id = match.group(2)
        queries = []

        if sp_type == "playlist":
            results = sp.playlist_tracks(sp_id)
            for item in results["items"]:
                track = item["track"]
                if track:
                    title = track["name"]
                    artist = track["artists"][0]["name"]
                    queries.append(f"{title} {artist}")

        elif sp_type == "album":
            results = sp.album_tracks(sp_id)
            album_data = sp.album(sp_id)
            album_artist = album_data["artists"][0]["name"]
            for track in results["items"]:
                title = track["name"]
                queries.append(f"{title} {album_artist}")

        return queries
    except Exception:
        return []

async def get_recommendations(seed_query: str) -> list[str]:
    try:
        # Pehle seed track dhundo
        results = sp.search(q=seed_query, type="track", limit=1)
        items = results["tracks"]["items"]
        if not items:
            return []

        seed_track_id = items[0]["id"]

        # Similar songs lo
        recs = sp.recommendations(seed_tracks=[seed_track_id], limit=5)
        queries = []
        for track in recs["tracks"]:
            title = track["name"]
            artist = track["artists"][0]["name"]
            queries.append(f"{title} {artist}")

        return queries
    except Exception:
        return []
