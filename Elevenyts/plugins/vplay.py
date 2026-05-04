import yt_dlp
from pyrogram import filters
from pytgcalls.types import MediaStream
from Elevenyts import app, call # Aapke main file se app aur call instance

# 360p High Performance Settings
ydl_opts = {
    "format": "best[height<=360][ext=mp4]/best[ext=mp4]/simple",
    "quiet": True,
    "no_warnings": True,
    "geo_bypass": True,
}

@app.on_message(filters.command(["vplay", "vstream"]))
async def vplay_handler(client, message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Bhai, YouTube link toh do!\nExample: `/vplay https://youtu.be/xyz`")

    url = message.text.split(None, 1)[1]
    status = await message.reply_text("🔍 Fetching 360p video stream...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info['url']
            title = info['title']

        # Call join karne ka logic
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

@app.on_message(filters.command(["vstop", "vleave", "vclear"]))
async def vstop_handler(client, message):
    try:
        # Forcefully leave the call
        await call.leave_group_call(message.chat.id)
        await message.reply_text("⏹ **Stream Stopped:** Video band kar di gayi hai.")
    except Exception as e:
        await message.reply_text(f"ℹ️ **Info:** Call pehle se hi band hai ya koi error hai.")

@app.on_message(filters.command(["vskip", "vnext"]))
async def vskip_handler(client, message):
    try:
        # Jab tak queue nahi hai, skip bhi leave ka kaam karega
        await call.leave_group_call(message.chat.id)
        await message.reply_text("⏩ **Skipped:** Agla video logic (queue) add karein.")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** {str(e)}")
