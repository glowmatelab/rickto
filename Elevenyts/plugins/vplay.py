import os
import re
from pyrogram import filters
from pytgcalls.types import MediaStream
from Elevenyts import app, call, lang, yt
from Elevenyts.helpers import Track


@app.on_message(filters.command(["vplay", "vstream"]) & filters.group & ~app.bl_users)
@lang.language()
async def vplay_handler(client, message):
    try:
        await message.delete()
    except:
        pass

    if len(message.command) < 2:
        return await message.reply_text("❌ YouTube link do bhai!")

    url = message.text.split(None, 1)[1].strip()
    status = await message.reply_text("🔍 YouTube link check kar raha hoon...")

    try:
        if not yt.valid(url):
            return await status.edit("❌ **Invalid YouTube URL!**")

        match = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
        if not match:
            return await status.edit("❌ **Video ID nahi mila!**")

        video_id = match.group(1)
        await status.edit("⏳ Video download ho raha hai...")

        # Track info fetch karo
        track = await yt.search(video_id, status.id, video=True)
        if not track:
            return await status.edit("❌ **Video nahi mila YouTube pe!**")

        # File download karo
        file_path = await yt.download(video_id, is_live=False, video=True)
        if not file_path or not os.path.exists(file_path):
            return await status.edit("❌ **Download failed!**")

        track.file_path = file_path
        track.video = True

        # play_media se bajao
        await call.play_media(
            chat_id=message.chat.id,
            message=status,
            media=track,
        )

    except Exception as e:
        await status.edit(f"❌ **Error:** {str(e)}")
