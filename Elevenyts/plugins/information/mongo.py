import re
from pymongo import MongoClient
from pyrogram import filters
from pyrogram.types import Message

from Elevenyts import app
from Elevenyts.helpers._admins import admin_check

mongo_url_pattern = re.compile(r"mongodb(?:\+srv)?:\/\/[^\s]+")


@app.on_message(filters.command("mongochk"))
@admin_check
async def mongo_command(client, message: Message):
    if len(message.command) < 2:
        await message.reply(
            "ᴘʟᴇᴀsᴇ ᴇɴᴛᴇʀ ʏᴏᴜʀ ᴍᴏɴɢᴏᴅʙ ᴜʀʟ ᴀғᴛᴇʀ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ\n\n"
            "<b>Usage:</b> <code>/mongochk your_mongodb_url</code>"
        )
        return

    mongo_url = message.command[1]

    if re.match(mongo_url_pattern, mongo_url):
        msg = await message.reply("⏳ <b>Checking MongoDB connection...</b>")
        try:
            mongo_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            mongo_client.server_info()
            await msg.edit_text("✅ <b>MongoDB URL valid hai aur connection successful!</b>")
        except Exception as e:
            await msg.edit_text(
                f"❌ <b>MongoDB connect nahi hua!</b>\n\n"
                f"<b>Error:</b> <code>{e}</code>"
            )
    else:
        await message.reply(
            "❌ <b>Invalid MongoDB URL format!</b>\n\n"
            "Sahi format:\n"
            "<code>mongodb://...</code> ya\n"
            "<code>mongodb+srv://...</code>"
        )
