import os
import asyncio
from gtts import gTTS
from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.errors import RPCError
from Elevenyts import app

@app.on_message(filters.command("info") & filters.reply)
async def info_handler(client, message):
    rep = message.reply_to_message
    status_msg = await message.reply_text("📡 Analyzing source...")
    
    try:
        if rep.sticker:
            sticker = rep.sticker
            
            if sticker.is_animated:
                st_type = "🎬 Animated (TGS)"
            elif sticker.is_video:
                st_type = "📹 Video (WEBM)"
            else:
                st_type = "🖼️ Static (PNG/WEBP)"

            # Premium emoji check
            premium_emoji_id = ""
            if sticker.premium_animation:
                premium_emoji_id = f"\n💠 **Premium Emoji ID:** `{sticker.custom_emoji_id or 'N/A'}`"

            info_text = (
                f"🎨 **Sticker Information**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **Sticker ID:** `{sticker.file_id}`\n"
                f"✨ **Emoji:** {sticker.emoji or 'None'}\n"
                f"📦 **Pack Short Name:** `{sticker.set_name or 'None'}`\n"
                f"⚙️ **Type:** {st_type}\n"
                f"📏 **Size:** {sticker.width}x{sticker.height}"
                f"{premium_emoji_id}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💬 **Current Chat ID:** `{message.chat.id}`"
            )

        elif rep.forward_from_chat:
            chat = rep.forward_from_chat
            info_text = (
                f"📢 **Forwarded Channel Info**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✨ **Title:** {chat.title}\n"
                f"🆔 **Channel ID:** `{chat.id}`\n"
                f"🔗 **Username:** @{chat.username or 'None'}\n"
                f"🛰 **Type:** {chat.type}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💬 **Current Chat ID:** `{message.chat.id}`"
            )
        
        elif rep.from_user:
            user = rep.from_user
            try:
                full_user = await client.get_chat(user.id)
                user_bio = full_user.bio or "No bio set"
            except:
                user_bio = "Private/Hidden"
            
            tag = "Standard User"
            if user.is_premium: tag = "💎 Premium"
            elif user.is_bot: tag = "🤖 Bot"
            
            info_text = (
                f"👤 **User Information**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✨ **Name:** {user.first_name}\n"
                f"🆔 **User ID:** `{user.id}`\n"
                f"🛡️ **Tag:** {tag}\n"
                f"📝 **Bio:** {user_bio}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📍 **In Group:** {message.chat.title or 'Private'}\n"
                f"🔢 **Group ID:** `{message.chat.id}`"
            )
            
        elif rep.sender_chat:
            chat = rep.sender_chat
            info_text = (
                f"🏢 **Sender Chat Info**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✨ **Title:** {chat.title}\n"
                f"🆔 **Chat ID:** `{chat.id}`\n"
                f"🔗 **Username:** @{chat.username or 'None'}\n"
                f"🛰 **Type:** {chat.type}\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
        else:
            info_text = "❌ I can't get info about this message."
            
        await status_msg.edit(info_text)
        
    except Exception as e:
        await status_msg.edit(f"❌ **Error:** `{str(e)}`")


@app.on_message(filters.command("id") & ~filters.reply)
async def fast_id(client, message):
    chat_type = message.chat.type
    info = (
        f"🆔 **Your ID:** `{message.from_user.id}`\n"
        f"💬 **This Chat ID:** `{message.chat.id}`\n"
        f"🛰 **Chat Type:** `{chat_type}`"
    )
    await message.reply_text(info)


# ─────────────────────────── /say ────────────────────────────

@app.on_message(filters.command("say"))
async def say_cmd(client, message):
    text = message.text.split(None, 1)
    if len(text) < 2:
        await message.reply_text("❌ Usage: `/send your message`")
        return
    await message.delete()
    await client.send_message(message.chat.id, text[1])


# ─────────────────────────── /psay ────────────────────────────

@app.on_message(filters.command("psend"))
async def psay_cmd(client, message):
    text = message.text.split(None, 1)
    if len(text) < 2:
        await message.reply_text("❌ Usage: `/psay your message`")
        return
    
    user = message.from_user
    if user.username:
        sender = f"@{user.username}"
    else:
        sender = user.first_name or "User"
    
    await message.delete()
    await client.send_message(message.chat.id, f"{sender}: {text[1]}")


# ─────────────────────────── /tts ────────────────────────────

@app.on_message(filters.command("tts"))
async def tts_cmd(client, message):
    text = message.text.split(None, 1)
    if len(text) < 2:
        await message.reply_text("❌ Usage: `/tts your text`")
        return
    
    tts_text = text[1]
    status = await message.reply_text("🔊 Generating voice...")
    
    os.makedirs("cache", exist_ok=True)
    audio_path = f"cache/tts_{message.id}.mp3"
    
    try:
        def _gen():
            tts = gTTS(text=tts_text, lang="hi")  # Hindi default, change to "en" for English
            tts.save(audio_path)
        
        await asyncio.to_thread(_gen)
        await status.delete()
        await message.reply_voice(audio_path)
    except Exception as e:
        await status.edit(f"❌ TTS Error: `{str(e)}`")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
