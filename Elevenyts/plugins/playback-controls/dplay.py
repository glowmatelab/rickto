"""
DirectPlay - Fixed single channel se random songs bajao
Command: /dplay
"""

import asyncio
import logging
import os
import random
import time

from pyrogram import filters
from pyrogram.errors import FloodWait, ChannelInvalid, ChannelPrivate, MessageIdInvalid, MessageDeleteForbidden, ChatSendPlainForbidden, ChatWriteForbidden
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from Elevenyts import app, db, tune, config
from Elevenyts.helpers import Media, can_manage_vc

logger = logging.getLogger(__name__)

# ── RAM state ──
_dp_played: dict[int, set] = {}
_dp_current_file: dict[int, str] = {}
_dp_ctrl_msg: dict[int, int] = {}


def _dp_button(chat_id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⏭ Play Next", callback_data=f"dp_next_{chat_id}")]])


def _cleanup_file(chat_id):
    path = _dp_current_file.pop(chat_id, None)
    if path and os.path.exists(path):
        try:
            os.remove(path)
            logger.info(f"[DirectPlay] Deleted: {path}")
        except Exception:
            pass


async def _get_userbot(chat_id):
    try:
        return await db.get_client(chat_id)
    except Exception:
        return None


async def _download_and_play(group_chat_id: int, status_msg=None):
    channel_id = config.DIRECT_PLAY_CHANNEL
    if not channel_id:
        return

    _cleanup_file(group_chat_id)

    async def safe_edit(text):
        if status_msg:
            try:
                await status_msg.edit_text(text)
            except Exception:
                pass

    await safe_edit("🔎 <b>Channel se track dhundh raha hoon...</b>")

    client = await _get_userbot(group_chat_id)
    if not client:
        await safe_edit("❌ Userbot nahi mila! String session check karo.")
        return

    # Channel history fetch
    played = _dp_played.setdefault(group_chat_id, set())
    all_msgs = []
    try:
        async for msg in client.get_chat_history(channel_id, limit=200):
            if msg.audio or msg.voice or msg.video or (
                msg.document and getattr(msg.document, "mime_type", "").startswith(("audio/", "video/"))
            ):
                all_msgs.append(msg)
    except (ChannelInvalid, ChannelPrivate) as e:
        await safe_edit(f"❌ Channel access error: <code>{e}</code>")
        return
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        return
    except Exception as e:
        await safe_edit(f"❌ History fetch error: <code>{e}</code>")
        return

    if not all_msgs:
        await safe_edit("❌ Channel mein koi audio/video nahi mila!")
        return

    unplayed = [m for m in all_msgs if m.id not in played]
    if not unplayed:
        played.clear()
        unplayed = all_msgs

    chosen = random.choice(unplayed)
    played.add(chosen.id)

    media_obj = chosen.audio or chosen.voice or chosen.video or chosen.document
    title = (getattr(media_obj, "title", None) or getattr(media_obj, "file_name", None) or f"Track #{chosen.id}")[:40]
    file_ext = (getattr(media_obj, "file_name", None) or "audio").rsplit(".", 1)[-1]
    file_id = getattr(media_obj, "file_unique_id", str(chosen.id))
    duration = getattr(media_obj, "duration", 0) or 0
    file_path = f"downloads/dp_{group_chat_id}_{file_id}.{file_ext}"
    is_video = bool(chosen.video) or (chosen.document and getattr(chosen.document, "mime_type", "").startswith("video/"))

    await safe_edit(f"⬇️ <b>Download:</b> <code>{title}</code>")

    try:
        if not os.path.exists(file_path):
            await client.download_media(chosen, file_name=file_path)
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        try:
            await client.download_media(chosen, file_name=file_path)
        except Exception as e:
            await safe_edit(f"❌ Download fail: <code>{e}</code>")
            return
    except Exception as e:
        await safe_edit(f"❌ Download fail: <code>{e}</code>")
        return

    _dp_current_file[group_chat_id] = file_path

    dur_str = time.strftime("%H:%M:%S" if duration >= 3600 else "%M:%S", time.gmtime(duration)) if duration else "?"

    media = Media(
        id=file_id, title=title, duration=dur_str, duration_sec=duration,
        file_path=file_path, message_id=status_msg.id if status_msg else 0,
        url=chosen.link or "", video=is_video,
    )

    await safe_edit(f"▶️ <b>Playing:</b> <code>{title}</code>")

    try:
        await tune.play_media(chat_id=group_chat_id, message=status_msg, media=media)
    except Exception as e:
        await safe_edit(f"❌ Play fail: <code>{e}</code>")
        _cleanup_file(group_chat_id)
        return

    ctrl_text = f"🎵 <b>DirectPlay</b>\n\n🎧 <b>{title}</b>\n⏱ <code>{dur_str}</code>\n\n<i>Channel se random song chal raha hai.</i>"

    old_ctrl_id = _dp_ctrl_msg.get(group_chat_id)
    if old_ctrl_id:
        try:
            await app.edit_message_text(group_chat_id, old_ctrl_id, ctrl_text, reply_markup=_dp_button(group_chat_id))
            return
        except Exception:
            pass

    try:
        sent = await app.send_message(group_chat_id, ctrl_text, reply_markup=_dp_button(group_chat_id))
        _dp_ctrl_msg[group_chat_id] = sent.id
    except Exception as e:
        logger.warning(f"[DirectPlay] Control msg fail: {e}")


@app.on_message(filters.command(["dplay"]) & filters.group & ~app.bl_users)
@can_manage_vc
async def dplay_cmd(_, m: Message):
    try:
        await m.delete()
    except Exception:
        pass

    if not config.DIRECT_PLAY_CHANNEL:
        try:
            await m.reply_text("❌ <b>DIRECT_PLAY_CHANNEL</b> .env mein set nahi hai!")
        except Exception:
            pass
        return

    _dp_played.pop(m.chat.id, None)
    _dp_ctrl_msg.pop(m.chat.id, None)

    try:
        status_msg = await m.reply_text("📡 <b>DirectPlay shuru ho raha hai...</b>")
    except Exception:
        status_msg = None

    asyncio.create_task(_download_and_play(m.chat.id, status_msg))


@app.on_callback_query(filters.regex(r"^dp_next_(-?\d+)$"))
async def dplay_next_cb(_, q: CallbackQuery):
    group_chat_id = int(q.matches[0].group(1))

    if q.message.chat.id != group_chat_id:
        await q.answer("❌ Wrong chat!", show_alert=True)
        return

    await q.answer("⏭ Next song aa raha hai...")

    try:
        await q.message.edit_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("⏳ Loading...", callback_data="dp_loading")]]))
    except Exception:
        pass

    asyncio.create_task(_download_and_play(group_chat_id, q.message))


@app.on_callback_query(filters.regex(r"^dp_loading$"))
async def dp_loading_cb(_, q: CallbackQuery):
    await q.answer("⏳ Load ho raha hai...", show_alert=False)
