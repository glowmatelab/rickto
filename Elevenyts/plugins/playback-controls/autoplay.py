from pyrogram import filters
from Elevenyts import app, AUTO_PLAY, call, yt
from Elevenyts.helpers import Track


@app.on_message(filters.command("autoplay") & filters.group)
async def autoplay(_, message):
    chat_id = message.chat.id

    if len(message.command) < 2:
        return await message.reply(
            "Usage:\n/autoplay song name\n/autoplay off"
        )

    query = " ".join(message.command[1:])

    # OFF
    if query.lower() == "off":
        AUTO_PLAY.pop(chat_id, None)
        return await message.reply("✅ Autoplay Disabled")

    # SAVE QUERY
    AUTO_PLAY[chat_id] = query

    await message.reply(
        f"✅ Autoplay Enabled\n🎵 Keyword: {query}"
    )

    # SEARCH SONG
    try:
        track = await yt.search(query, 0)

        if not track:
            return await message.reply("❌ Song not found")

        track.is_autoplay = True

        # DOWNLOAD
        track.file_path = await yt.download(
            track.id,
            is_live=track.is_live
        )

        if not track.file_path:
            return await message.reply("❌ Download failed")

        # PLAY DIRECTLY
        await call.play_media(
            chat_id=chat_id,
            message=None,
            media=track
        )

    except Exception as e:
        await message.reply(f"❌ Error:\n{e}")
