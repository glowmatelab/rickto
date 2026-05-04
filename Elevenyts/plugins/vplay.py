import yt_dlp
from pyrogram import filters
from pytgcalls.types import MediaStream
from Elevenyts import app, call, tune, lang

# 360p High Performance Settings
ydl_opts = {
    "format": "best[height<=360][ext=mp4]/best[ext=mp4]/simple",
    "quiet": True,
    "no_warnings": True,
    "geo_bypass": True,
}

@app.on_message(filters.command(["vplay", "vstream"]) & filters.group & ~app.bl_users)
@lang.language()
async def vplay_handler(client, message):
    # Auto-delete command message
    try:
        await message.delete()
    except:
        pass

    if len(message.command) < 2:
        return await message.reply_text("❌ Bhai, YouTube link toh do!\nExample: `/vplay https://youtu.be/xyz`")

    url = message.text.split(None, 1)[1]
    status = await message.reply_text("🔍 Fetching 360p video stream...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info['url']
            title = info['title']

        # Call join karne ka logic with optimization flags
        await call.join_group_call(
            message.chat.id,
            MediaStream(
                stream_url,
                video_flags="-preset superfast -tune zerolatency",
            ),
        )
        await status.edit(f"🎬 **Now Playing:** {title}\n✅ **Quality:** 360p (Optimized)")

    except Exception as e:
        await status.edit(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command(["vstop", "vleave", "stop", "end"]) & filters.group & ~app.bl_users)
@lang.language()
async def vstop_handler(client, message):
    # Auto-delete command message
    try:
        await message.delete()
    except:
        pass

    try:
        # Framework ke tune.py se stop_playback call kar rahe hain 
        # Taaki database aur call dono sahi se clear ho jayein
        await tune.stop_playback(message.chat.id)
        await message.reply_text("⏹ **Stream Stopped:** Video band kar di gayi hai.")
    except Exception as e:
        # Agar tune.py fail ho toh direct leave try karega
        try:
            await call.leave_group_call(message.chat.id)
            await message.reply_text("⏹ **Stream Stopped.**")
        except:
            await message.reply_text("ℹ️ Stream pehle se hi band hai.")
