import yt_dlp
from pyrogram import filters
from pytgcalls.types import MediaStream
from Elevenyts import app, call

# Strict 360p settings for smooth streaming
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
    status = await message.reply_text("Fetching 360p video stream... thoda ruko.")

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
        await status.edit(f"Playing Video: {title}\nResolution: 360p")

    except Exception as e:
        await status.edit(f"Error: {str(e)}")

@app.on_message(filters.command("vstop"))
async def vstop_handler(client, message):
    try:
        await call.leave_group_call(message.chat.id)
        await message.reply_text("Video stream band kar di gayi hai.")
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")

@app.on_message(filters.command("vskip"))
async def vskip_handler(client, message):
    try:
        # Abhi current stream stop karke message dega
        # Agle video ka logic queue system add karne par hi chalega
        await call.leave_group_call(message.chat.id)
        await message.reply_text("Current video skip kar di gayi hai.")
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")
