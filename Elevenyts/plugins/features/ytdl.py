# Elevenyts/plugins/features/ytdl.py
# YouTube Downloader Plugin - /download command

import os
import asyncio
import logging
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from Elevenyts import app, yt

logger = logging.getLogger(__name__)


# ─── Helper: YouTube link nikalna ───────────────────────────────────────────

def extract_yt_link(message: Message):
    """Message ya uske reply se YouTube link extract karo."""
    targets = [message]
    if message.reply_to_message:
        targets.append(message.reply_to_message)

    for msg in targets:
        text = msg.text or msg.caption or ""
        entities = msg.entities or msg.caption_entities or []
        for entity in entities:
            from pyrogram import enums
            if entity.type == enums.MessageEntityType.URL:
                link = text[entity.offset: entity.offset + entity.length]
                if yt.valid(link):
                    return link.split("&si")[0].split("?si")[0]
            elif entity.type == enums.MessageEntityType.TEXT_LINK:
                if yt.valid(entity.url):
                    return entity.url
        # Plain text me link check
        for word in text.split():
            if yt.valid(word):
                return word.split("&si")[0].split("?si")[0]
    return None


# ─── /download command ───────────────────────────────────────────────────────

@app.on_message(filters.command("download") & filters.group)
async def download_cmd(_, message: Message):
    """
    Usage:
      - Kisi YouTube link waale message ko reply karo + /download
      - Ya /download ke saath seedha link do
    Bot Audio / Video ke 2 inline buttons dikhayega.
    """
    link = extract_yt_link(message)

    if not link:
        await message.reply_text(
            "❌ **YouTube link nahi mila!**\n\n"
            "**Kaise use karo:**\n"
            "1. YouTube link bhejo\n"
            "2. Us message ko reply karo `/download` likhke\n\n"
            "Ya seedha: `/download https://youtu.be/xxxxx`"
        )
        return

    # Video ID nikalo URL se
    import re
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", link)
    if not match:
        await message.reply_text("❌ Valid YouTube video ID nahi mila.")
        return

    video_id = match.group(1)

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"ytdl_audio_{video_id}"),
            InlineKeyboardButton("🎬 Video (MP4)", callback_data=f"ytdl_video_{video_id}"),
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data="ytdl_cancel"),
        ]
    ])

    await message.reply_text(
        f"📥 **Download kya chahiye?**\n\n"
        f"🔗 `{link}`",
        reply_markup=buttons
    )


# ─── Callback: Audio / Video button press ───────────────────────────────────

@app.on_callback_query(filters.regex(r"^ytdl_(audio|video|cancel)_?(.*)$"))
async def ytdl_callback(_, query: CallbackQuery):
    data = query.data

    # Cancel
    if data == "ytdl_cancel":
        await query.message.delete()
        await query.answer("Cancelled ✅")
        return

    parts = data.split("_", 2)   # ['ytdl', 'audio'/'video', 'video_id']
    if len(parts) < 3:
        await query.answer("Invalid request", show_alert=True)
        return

    dl_type = parts[1]           # 'audio' or 'video'
    video_id = parts[2]
    is_video = (dl_type == "video")

    await query.answer(f"{'🎬 Video' if is_video else '🎵 Audio'} download ho raha hai...")
    status_msg = await query.message.edit_text(
        f"⏳ **{'Video' if is_video else 'Audio'} download ho raha hai...**\n"
        f"🆔 `{video_id}`\n\n"
        "_Thodi der wait karo..._"
    )

    file_path = None
    try:
        # Download (existing youtube.py ka download() use kar rahe hain)
        file_path = await yt.download(video_id=video_id, is_live=False, video=is_video)

        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text("❌ Download fail ho gaya. Baad mein try karo.")
            return

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

        # Telegram file size limit: 2GB (bot API: 50MB, local API: 2GB)
        # Simple check for 50MB (normal bot)
        if file_size_mb > 50:
            await status_msg.edit_text(
                f"❌ File bahut badi hai ({file_size_mb:.1f} MB).\n"
                "Telegram 50MB se badi files allow nahi karta."
            )
            return

        await status_msg.edit_text(
            f"📤 **Telegram pe bhej raha hoon...**\n"
            f"📦 Size: `{file_size_mb:.1f} MB`"
        )

        chat_id = query.message.chat.id

        if is_video:
            await app.send_video(
                chat_id=chat_id,
                video=file_path,
                caption=f"🎬 **Video** | `{video_id}`\n_Downloaded by bot_",
            )
        else:
            await app.send_audio(
                chat_id=chat_id,
                audio=file_path,
                caption=f"🎵 **Audio** | `{video_id}`\n_Downloaded by bot_",
            )

        # Status message delete karo
        await status_msg.delete()

    except Exception as e:
        logger.error(f"ytdl_callback error: {e}")
        try:
            await status_msg.edit_text(f"❌ Error: `{e}`")
        except Exception:
            pass

    finally:
        # ✅ FILE TURANT DELETE - memory waste nahi hogi
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"🗑️ Deleted after send: {file_path}")
            except Exception as e:
                logger.warning(f"File delete failed: {e}")
