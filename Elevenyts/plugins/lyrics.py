import aiohttp
from pyrogram import filters
from Elevenyts import app

@app.on_message(filters.command("lyrics"))
async def get_lyrics(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Bhai, gaane ka naam toh likho! \nExample: /lyrics Tum Hi Ho")

    query = message.text.split(None, 1)[1]
    status_msg = await message.reply_text(f"Searching lyrics for: {query}")

    api_url = f"https://test-0k.onrender.com/lyrics/?song={query.replace(' ', '%20')}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=10) as resp:
                if resp.status != 200:
                    return await status_msg.edit("Lyrics nahi mile, shayad spelling galat hai ya gaana database mein nahi hai.")
                
                data = await resp.json()
                
                meta = data.get("metadata", {})
                title = meta.get("trackName", query.title())
                artist = meta.get("artistName", "Unknown Artist")
                album = meta.get("albumName", "N/A")
                
                lyrics = data.get("lyrics") or data.get("syncedLyrics")
                
                if not lyrics:
                    return await status_msg.edit("Is gaane ke lyrics khali hain.")

                header = (
                    f"Song: {title}\n"
                    f"Artist: {artist}\n"
                    f"Album: {album}\n"
                    f"----------------------------\n\n"
                )
                
                if len(header + lyrics) > 4096:
                    lyrics = lyrics[:4000] + "..."

                await status_msg.edit(f"{header}{lyrics}")

    except Exception as e:
        await status_msg.edit(f"Error: {str(e)}")
