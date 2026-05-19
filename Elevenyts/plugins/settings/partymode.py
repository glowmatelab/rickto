import random
from pyrogram import filters
from pyrogram.types import Message
from Elevenyts import app

# Stickers list
PARTY_STICKERS = [
    "CAACAgUAAyEFAATSD3CtAAII2GoMYhz9GDBgF7gTTWKrBa9b3F0iAAKpHQACvTpZVBMwEfUUJZSuHgQ",
]

# ON hain jinke liye
party_chats = set()

@app.on_message(filters.command(["partymode", "stickermode"]) & filters.group)
async def partymode_cmd(_, m: Message):
    chat_id = m.chat.id
    if len(m.command) < 2:
        status = "✅ ON" if chat_id in party_chats else "❌ OFF"
        return await m.reply(f"🎉 Party Mode: {status}\n\nUse: /partymode on | off")
    
    if m.command[1].lower() == "on":
        party_chats.add(chat_id)
        await m.reply("🎉 Party Mode ON! Ab har play ke baad sticker aayega! 🕺")
    else:
        party_chats.discard(chat_id)
        await m.reply("😴 Party Mode OFF!")
