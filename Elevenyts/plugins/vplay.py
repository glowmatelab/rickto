import yt_dlp
from pyrogram import filters
from pytgcalls.types import MediaStream
from Elevenyts import app, call

# 360p Optimized Settings
ydl_opts = {
    "format": "best[height<=360][ext=mp4]/best[ext=mp4]/simple",
    "quiet": True,
    "no_warnings": True,
    "geo_bypass": True,
}

@app.on_message(filters.command(["vplay", "vstream"]))
async def vplay_handler(client, message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Bhai, YouTube link toh do!")

    url = message.text.split(None, 1)[1]
    status = await message.reply_text("🔍 Fetching 360p video stream...")

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
        # Yahan hum wahi title aur quality dikha rahe hain jo buttons mein show hoti hai
        await status.edit(f"🎬 **Now Playing:** {title}\n✅ **Quality:** 360p")

    except Exception as e:
        await status.edit(f"❌ **Error:** {str(e)}")

# STOP COMMAND - Linked with 'controls stop {chat_id}' logic
@app.on_message(filters.command(["vstop", "vleave", "vclear"]))
async def vstop_handler(client, message):
    try:
        # Tumhare inline button ka 'stop' logic yahan force trigger hoga
        await call.leave_group_call(message.chat.id)
        await message.reply_text("⏹ **Stopped:** Video stream band kar di gayi hai.")
    except Exception as e:
        await message.reply_text("ℹ️ Call pehle se hi band hai.")

# SKIP COMMAND - Linked with 'controls skip {chat_id}' logic
@app.on_message(filters.command(["vskip", "vnext"]))
async def vskip_handler(client, message):
    try:
        # Skip ke liye hum current stream ko drop kar rahe hain
        # Agar queue system active hai, toh call.leave isse next track par bhej dega
        await call.leave_group_call(message.chat.id)
        await message.reply_text("⏩ **Skipped:** Current video skip kar di gayi.")
    except Exception as e:
        await message.reply_text("❌ Skip karne mein dikat aa rahi hai.")
