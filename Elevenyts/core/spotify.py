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

        oembed_url = f"https://open.spotify.com/oembed?url={url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(oembed_url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                title = data.get("title")
                return title

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

        async with aiohttp.ClientSession() as session:
            if sp_type == "playlist":
                api_url = f"https://api.spotifydown.com/trackList/playlist/{sp_id}"
            elif sp_type == "album":
                api_url = f"https://api.spotifydown.com/trackList/album/{sp_id}"
            else:
                return []

            headers = {
                "origin": "https://spotifydown.com",
                "referer": "https://spotifydown.com"
            }
            async with session.get(api_url, headers=headers) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                tracks = data.get("trackList", [])
                for track in tracks:
                    title = track.get("title", "")
                    artist = track.get("artists", "")
                    if title:
                        queries.append(f"{title} {artist}")

        return queries

    except Exception:
        return []
