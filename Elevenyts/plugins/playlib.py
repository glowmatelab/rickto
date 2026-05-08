from pyrogram import filters
from pyrogram.types import Message
from pytgcalls.types import MediaStream

from Elevenyts import app, call

LIBRARY_CHANNEL = -1003956796095


@app.on_message(filters.command("playlib") & filters.group)
async def playlib(_, message: Message):

    await message.reply_text("playlib command received")

    async for msg in app.get_chat_history(LIBRARY_CHANNEL, limit=10):

        if msg.audio:

            await message.reply_text("song found")

            file_path = await msg.download()

            await message.reply_text(f"downloaded: {file_path}")

            try:

                await call.join_group_call(
                    message.chat.id,
                    MediaStream(file_path),
                )

                await message.reply_text("started playing")

            except Exception as e:

                await message.reply_text(str(e))

            return

    await message.reply_text("no audio found")
