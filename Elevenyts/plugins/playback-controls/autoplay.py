from pyrogram import filters

from Elevenyts import app, AUTO_PLAY, call, yt, queue


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

    msg = await message.reply(
        f"✅ Autoplay Enabled\n🎵 Keyword: {query}"
    )

    try:
        # SEARCH SONG
        track = await yt.search(query, 0)

        if not track:
            return await msg.edit_text("❌ Song not found")

        track.is_autoplay = True

        # DOWNLOAD SONG
        track.file_path = await yt.download(
            track.id,
            is_live=track.is_live
        )

        if not track.file_path:
            return await msg.edit_text("❌ Download failed")

        # ADD TO QUEUE
        queue.put(chat_id, track)

        # START PLAYING
        await call.play_media(
            chat_id=chat_id,
            message=msg,
            media=track
        )

    except Exception as e:
        await msg.edit_text(f"❌ Error:\n{e}")
