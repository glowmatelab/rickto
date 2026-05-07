from pyrogram import filters
from Elevenyts import app
from Elevenyts.storage import AUTO_PLAY


@app.on_message(filters.command("autoplay") & filters.group)
async def autoplay(_, message):
    chat_id = message.chat.id

    if len(message.command) < 2:
        return await message.reply(
            "Usage:\n/autoplay song name\n/autoplay off"
        )

    query = " ".join(message.command[1:])

    # Turn Off
    if query.lower() == "off":
        AUTO_PLAY.pop(chat_id, None)

        return await message.reply(
            "✅ Autoplay Disabled"
        )

    # Save keyword
    AUTO_PLAY[chat_id] = query

    await message.reply(
        f"✅ Autoplay Enabled\n🎵 Keyword: {query}"
    )
