import re
from ytmusicapi import YTMusic

ytmusic = YTMusic()

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
        if sp_type != "track":
            return None

        sp_id = match.group(2)
        results = ytmusic.search(sp_id, filter="songs")
        if not results:
            return None

        title = results[0].get("title", "")
        artists = results[0].get("artists", [])
        artist = artists[0].get("name", "") if artists else ""
        return f"{title} {artist}"

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
            results = ytmusic.search(sp_id, filter="songs")
            for item in results[:20]:
                title = item.get("title", "")
                artists = item.get("artists", [])
                artist = artists[0].get("name", "") if artists else ""
                if title:
                    queries.append(f"{title} {artist}")

        elif sp_type == "album":
            results = ytmusic.search(sp_id, filter="albums")
            if results:
                browse_id = results[0].get("browseId")
                if browse_id:
                    album = ytmusic.get_album(browse_id)
                    album_artist = album.get("artists", [{}])[0].get("name", "")
                    for track in album.get("tracks", []):
                        title = track.get("title", "")
                        if title:
                            queries.append(f"{title} {album_artist}")

        return queries
    except Exception:
        return []

async def get_recommendations(seed_query: str) -> list[str]:
    try:
        results = ytmusic.search(seed_query, filter="songs")
        if not results:
            return []

        queries = []
        for item in results[:5]:
            title = item.get("title", "")
            artists = item.get("artists", [])
            artist = artists[0].get("name", "") if artists else ""
            if title:
                queries.append(f"{title} {artist}")

        return queries
    except Exception:
        return []
