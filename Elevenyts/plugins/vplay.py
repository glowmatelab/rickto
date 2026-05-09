import os
import re
from pyrogram import filters
from pytgcalls.types import MediaStream
from Elevenyts import app, call, lang, yt


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

    url = message.text.split(None, 1)[1].strip()
    status = await message.reply_text("🔍 YouTube link check kar raha hoon...")

    try:
        # Validate URL
        if not yt.valid(url):
            return await status.edit("❌ Invalid YouTube URL!**\nSahi YouTube link do bhai.")

        # Extract video ID from URL
        match = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
        if not match:
            return await status.edit("❌ Video ID nahi mila!**\nSahi YouTube link do.")

        video_id = match.group(1)
        await status.edit("⏳ Video download ho raha hai... thoda ruk bhai 🎬")

        # Use the existing API-based download (no yt-dlp, no bot detection issue)
        file_path = await yt.download(video_id, is_live=False, video=True)

        if not file_path or not os.path.exists(file_path):
            return await status.edit(
                "❌ Download failed!\n"
                "API se video nahi aaya. Thodi der baad try kar."
            )

        # Try to get title from search cache
        title = f"YouTube [{video_id}]"
        try:
            track = await yt.search(video_id, message.id, video=True)
            if track and track.title:
                title = track.title
        except:
            pass

        # Stream the downloaded file
        await call.join_group_call(
            message.chat.id,
            MediaStream(file_path),
        )

        await status.edit(
            f"🎬 Now Playing: {title}\n"
            f"✅ Source:** YouTube API (No bot detection)"
        )

    except Exception as e:
        err = str(e)
        if "Sign in" in err or "bot" in err.lower():
            await status.edit(
                "❌ YouTube ne block kar diya!**\n"
                "Bot detection issue hai. Admin se contact karo."
            )
        elif "unavailable" in err.lower() or "not available" in err.lower():
            await status.edit("❌ Video unavailable!**\nShayad private ya deleted ho gaya.")
        else:
            await status.edit(f"❌ **Error:** {err}")
