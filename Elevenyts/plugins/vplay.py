import yt_dlp
from pyrogram import filters
from pytgcalls.types import MediaStream
from Elevenyts import app, call

# Strict 360p options
ydl_opts = {
    "format": "best[height<=360][ext=mp4]/best[ext=mp4]/simple",
    "quiet": True,
    "no_warnings": True,
}

@app.on_message(filters.command("vplay"))
async def vplay_handler(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Bhai, YouTube link toh do! \nExample: /vplay https://youtu.be/...")

    url = message.text.split(None, 1)[1]
    status = await message.reply_text("Fetching 360p video stream...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info['url']
            title = info['title']

        await call.join_group_call(
            message.chat.id,
            MediaStream(
                stream_url,
                video_flags="-preset superfast -tune zerolatency",
            ),
        )
        await status.edit(f"Playing Video: {title}\nResolution: 360p (Ultra Optimized)")

    except Exception as e:
        await status.edit(f"Error: {str(e)}")
