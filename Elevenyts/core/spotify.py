import re
import aiohttp

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

        # Spotify oembed API se title nikalo — free, no credentials
        oembed_url = f"https://open.spotify.com/oembed?url={url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(oembed_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                title = data.get("title")
                return title  # "Tum Hi Ho - Arijit Singh" jaisa hoga

    except Exception:
        return None

async def get_playlist(url: str) -> list[str]:
    try:
        match = SPOTIFY_REGEX.match(url)
        if not match:
            return []

        sp_type = match.group(1)
        sp_id = match.group(2)

        if sp_type == "playlist":
            # Playlist ke liye individual tracks ke oembed call karenge
            # Pehle playlist page se track IDs nikalo
            async with aiohttp.ClientSession() as session:
                api_url = f"https://api.spotify.com/v1/playlists/{sp_id}/tracks"
                # Public playlist embed URL se kaam nahi karta
                # Isliye oembed se sirf playlist title milega
                # Workaround: playlist URL ka oembed title YouTube pe search karo
                oembed_url = f"https://open.spotify.com/oembed?url={url}"
                async with session.get(oembed_url) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    playlist_title = data.get("title", "")
                    # Playlist title se YouTube pe search karke tracks lo
                    return [playlist_title]

        elif sp_type == "album":
            oembed_url = f"https://open.spotify.com/oembed?url={url}"
            async with aiohttp.ClientSession() as session:
                async with session.get(oembed_url) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    album_title = data.get("title", "")
                    return [album_title]

        return []

    except Exception:
        return []
