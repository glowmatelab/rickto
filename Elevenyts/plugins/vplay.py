import yt_dlp
from pyrogram import filters
from pytgcalls.types import MediaStream
from Elevenyts import app, call, lang

# 360p Optimized Settings for Antavion
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
        return await message.reply_text("❌ YouTube link do bhai!")

    url = message.text.split(None, 1)[1]
    status = await message.reply_text("🔍 Fetching 360p video stream...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info['url']
            title = info['title']

        # Direct stream without local download
        await call.join_group_call(
            message.chat.id,
            MediaStream(
                stream_url,
                video_flags="-preset superfast -tune zerolatency",
            ),
        )
        await status.edit(f"🎬 **Now Playing:** {title}\n✅ **Quality:** 360p")

    except Exception as e:
        await status.edit(f"❌ **Error:** {str(e)}")
