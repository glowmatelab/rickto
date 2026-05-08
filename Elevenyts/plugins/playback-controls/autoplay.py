import random
from pyrogram import filters
from Elevenyts import app, call, yt, queue
from Elevenyts.storage import AUTO_PLAY, PLAYED_IDS

@app.on_message(filters.command("autoplay") & filters.group)
async def autoplay(_, message):
    chat_id = message.chat.id
    if len(message.command) < 2:
        return await message.reply(
            "Usage:\n/autoplay song name\n/autoplay off"
        )
    query = " ".join(message.command[1:])

    # DISABLE
    if query.lower() == "off":
        AUTO_PLAY.pop(chat_id, None)
        PLAYED_IDS.pop(chat_id, None)
        return await message.reply("✅ Autoplay Disabled")

    # SAVE KEYWORD
    AUTO_PLAY[chat_id] = query
    await message.reply(
        text=(
        "⚙️ ᴀᴜᴛᴏᴘʟᴀʏ sʏsᴛᴇᴍ ᴀᴄᴛɪᴠᴀᴛᴇᴅ\n"
        f"<blockquote><b>✅ sᴛᴀᴛᴜs:</b> ᴇɴᴀʙʟᴇᴅ\n"
        f"<b>ʙᴀsᴇᴅ ᴏɴ:</b> `{query}`</blockquote>\n"
        "<i>ɴᴏᴡ ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴘʟᴀʏ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢs! ⚡</i>"
        )
            
    )

    try:
        # SEARCH
        track = await yt.search(query, random.randint(0, 4))
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

        # TRACK PLAYED ID
        if chat_id not in PLAYED_IDS:
            PLAYED_IDS[chat_id] = set()
        PLAYED_IDS[chat_id].add(track.id)

        # ADD TO QUEUE (clear pehle taaki loop na ho)
        queue.clear(chat_id)
        queue.add(chat_id, track)

        # PLAY
        await call.play_media(
            chat_id=chat_id,
            message=None,
            media=track
        )
    except Exception as e:
        await message.reply(f"❌ Error:\n{e}")
