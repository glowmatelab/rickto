"""
DirectPlay Plugin
-----------------
Ek specific Telegram channel se random songs uthao aur VC mein bajao.
Channel = database. Koi MongoDB nahi chahiye songs ke liye.

Commands:
  /directplay <channel_id>  — Channel set karo aur pehla random song bajao
  /directplay stop          — Band karo
  /directplay status        — Current channel dekho

Callback:
  dp_next_<chat_id>         — Next random song bajao (button se)

FIXES:
- is_directplay_active() + handle_stream_end() add kiya calls.py ke liye
- create_task wrapper _safe_download_and_play() add kiya — silent crash fix
- asyncio.create_task seedha nahi, wrapper se jaayega ab
"""

import asyncio
import logging
import os
import random
import time

from pyrogram import filters
from pyrogram.errors import (
    ChannelInvalid,
    ChannelPrivate,
    ChatAdminRequired,
    FloodWait,
    MessageDeleteForbidden,
    MessageIdInvalid,
    ChatSendPlainForbidden,
    ChatWriteForbidden,
)
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from Elevenyts import app, db, tune
from Elevenyts.helpers import Media, can_manage_vc

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  In-memory state
# ─────────────────────────────────────────────

# { group_chat_id : channel_id }
_dp_channels: dict[int, int] = {}

# { group_chat_id : set(message_ids) } — already played track IDs
_dp_played: dict[int, set] = {}

# { group_chat_id : str } — current downloaded file path (cleanup ke liye)
_dp_current_file: dict[int, str] = {}

# { group_chat_id : int } — control message id (edit karne ke liye)
_dp_ctrl_msg: dict[int, int] = {}


# ─────────────────────────────────────────────
#  calls.py ke liye public interface
# ─────────────────────────────────────────────

def is_directplay_active(chat_id: int) -> bool:
    """calls.py check karega ki directplay chal raha hai ya nahi."""
    return chat_id in _dp_channels


async def handle_stream_end(chat_id: int):
    """
    calls.py ke StreamEnded event se yeh call hoga.
    Button wala manual next alag hai — yeh sirf auto-next ke liye hai.
    """
    if chat_id not in _dp_channels:
        return
    logger.info(f"[DirectPlay] StreamEnded for {chat_id}, auto-next trigger...")
    asyncio.create_task(_safe_download_and_play(chat_id))


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

async def _safe_download_and_play(chat_id: int, status_msg=None):
    """Wrapper — exceptions silently drop nahi honge ab. Logs mein dikhega."""
    try:
        await _download_and_play(chat_id, status_msg)
    except Exception as e:
        logger.error(f"[DirectPlay] Task crashed for {chat_id}: {e}", exc_info=True)


async def _get_userbot(chat_id: int):
    """Group ke liye assigned userbot client return karo."""
    try:
        return await db.get_client(chat_id)
    except Exception:
        return None


def _dp_button(chat_id: int) -> InlineKeyboardMarkup:
    """Play Next button."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⏭ Play Next", callback_data=f"dp_next_{chat_id}")]]
    )


def _cleanup_file(chat_id: int):
    """Purani downloaded file disk se delete karo."""
    path = _dp_current_file.pop(chat_id, None)
    if path and os.path.exists(path):
        try:
            os.remove(path)
            logger.info(f"[DirectPlay] Deleted cached file: {path}")
        except Exception as e:
            logger.warning(f"[DirectPlay] Could not delete {path}: {e}")


async def _fetch_random_track(chat_id: int, channel_id: int) -> tuple[Message, str] | tuple[None, None]:
    """
    Channel se ek random audio/video message uthao.
    Already played wale skip karo.
    Agar sab play ho gaye to played list reset karo (loop).
    """
    played = _dp_played.setdefault(chat_id, set())

    client = await _get_userbot(chat_id)
    if not client:
        logger.error(f"[DirectPlay] No userbot client available for {chat_id}")
        return None, None

    all_msgs = []
    try:
        async for msg in client.get_chat_history(channel_id, limit=200):
            if msg.audio or msg.voice or msg.video or (
                msg.document and getattr(msg.document, "mime_type", "").startswith(("audio/", "video/"))
            ):
                all_msgs.append(msg)
    except (ChannelInvalid, ChannelPrivate, ChatAdminRequired) as e:
        logger.error(f"[DirectPlay] Channel access error {channel_id}: {e}")
        return None, None
    except FloodWait as fw:
        logger.warning(f"[DirectPlay] FloodWait {fw.value}s during history fetch")
        await asyncio.sleep(fw.value)
        return None, None
    except Exception as e:
        logger.error(f"[DirectPlay] get_chat_history error: {e}", exc_info=True)
        return None, None

    if not all_msgs:
        return None, None

    unplayed = [m for m in all_msgs if m.id not in played]
    if not unplayed:
        played.clear()
        unplayed = all_msgs

    chosen = random.choice(unplayed)
    played.add(chosen.id)

    media = chosen.audio or chosen.voice or chosen.video or chosen.document
    title = (
        getattr(media, "title", None)
        or getattr(media, "file_name", None)
        or f"Track #{chosen.id}"
    )
    title = title[:40]

    return chosen, title


async def _download_and_play(group_chat_id: int, status_msg: Message | None = None):
    """
    Core function:
    1. Purani file delete karo
    2. Channel se random track uthao
    3. Download karo
    4. VC mein play karo
    5. Control message bhejo/edit karo
    """
    channel_id = _dp_channels.get(group_chat_id)
    if not channel_id:
        return

    _cleanup_file(group_chat_id)

    async def safe_edit(text: str):
        if status_msg:
            try:
                await status_msg.edit_text(text)
            except (MessageIdInvalid, MessageDeleteForbidden, FloodWait):
                pass
            except Exception:
                pass

    await safe_edit("🔎 <b>Channel se track dhundh raha hoon...</b>")

    msg, title = await _fetch_random_track(group_chat_id, channel_id)
    if not msg:
        await safe_edit(
            "❌ <b>Channel mein koi audio/video nahi mila!</b>\n\n"
            "Channel mein songs upload karo aur dobara try karo."
        )
        return

    await safe_edit(f"⬇️ <b>Download ho raha hai:</b> <code>{title}</code>")

    client = await _get_userbot(group_chat_id)
    if not client:
        await safe_edit("❌ Userbot client nahi mila! String session check karo.")
        return

    media_obj = msg.audio or msg.voice or msg.video or msg.document
    file_ext = (getattr(media_obj, "file_name", None) or "audio").rsplit(".", 1)[-1]
    file_id = getattr(media_obj, "file_unique_id", str(msg.id))
    duration = getattr(media_obj, "duration", 0) or 0
    file_path = f"downloads/dp_{group_chat_id}_{file_id}.{file_ext}"
    is_video = bool(msg.video) or (
        msg.document and getattr(msg.document, "mime_type", "").startswith("video/")
    )

    try:
        if not os.path.exists(file_path):
            await client.download_media(msg, file_name=file_path)
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
        try:
            await client.download_media(msg, file_name=file_path)
        except Exception as e:
            await safe_edit(f"❌ Download fail hua: <code>{e}</code>")
            logger.error(f"[DirectPlay] Download fail after FloodWait: {e}")
            return
    except Exception as e:
        await safe_edit(f"❌ Download fail hua: <code>{e}</code>")
        logger.error(f"[DirectPlay] Download fail: {e}")
        return

    _dp_current_file[group_chat_id] = file_path

    if duration >= 3600:
        dur_str = time.strftime("%H:%M:%S", time.gmtime(duration))
    elif duration > 0:
        dur_str = time.strftime("%M:%S", time.gmtime(duration))
    else:
        dur_str = "?"

    media = Media(
        id=file_id,
        title=title,
        duration=dur_str,
        duration_sec=duration,
        file_path=file_path,
        message_id=status_msg.id if status_msg else 0,
        url=msg.link or "",
        video=is_video,
    )

    await safe_edit(f"▶️ <b>Play ho raha hai:</b> <code>{title}</code>")

    try:
        await tune.play_media(
            chat_id=group_chat_id,
            message=status_msg,
            media=media,
        )
    except Exception as e:
        await safe_edit(f"❌ Play fail hua: <code>{e}</code>")
        logger.error(f"[DirectPlay] play_media fail: {e}", exc_info=True)
        _cleanup_file(group_chat_id)
        return

    # Control message bhejo (edit ya naya)
    ctrl_text = (
        f"🎵 <b>DirectPlay</b>\n\n"
        f"🎧 <b>{title}</b>\n"
        f"⏱ Duration: <code>{dur_str}</code>\n\n"
        f"<i>Channel se random song bajaya ja raha hai.</i>"
    )

    old_ctrl_id = _dp_ctrl_msg.get(group_chat_id)
    if old_ctrl_id:
        try:
            await app.edit_message_text(
                group_chat_id,
                old_ctrl_id,
                ctrl_text,
                reply_markup=_dp_button(group_chat_id),
            )
            return
        except Exception:
            pass  # Edit fail — naya bhejo

    try:
        sent = await app.send_message(
            group_chat_id,
            ctrl_text,
            reply_markup=_dp_button(group_chat_id),
        )
        _dp_ctrl_msg[group_chat_id] = sent.id
    except (ChatSendPlainForbidden, ChatWriteForbidden):
        pass
    except Exception as e:
        logger.warning(f"[DirectPlay] Control message send fail: {e}")

    # ── Koi sleep loop nahi ──
    # Auto-next ab calls.py ke StreamEnded → handle_stream_end() se hoga.


# ─────────────────────────────────────────────
#  Commands
# ─────────────────────────────────────────────

@app.on_message(
    filters.command(["directplay", "dp"]) & filters.group & ~app.bl_users
)
@can_manage_vc
async def directplay_cmd(_, m: Message):
    try:
        await m.delete()
    except Exception:
        pass

    # ── STOP ──
    if len(m.command) == 2 and m.command[1].lower() == "stop":
        if m.chat.id in _dp_channels:
            _dp_channels.pop(m.chat.id)
            _dp_played.pop(m.chat.id, None)
            _cleanup_file(m.chat.id)
            _dp_ctrl_msg.pop(m.chat.id, None)
            try:
                await m.reply_text("⏹ <b>DirectPlay band kar diya.</b>")
            except Exception:
                pass
        else:
            try:
                await m.reply_text("❌ DirectPlay abhi chal nahi raha.")
            except Exception:
                pass
        return

    # ── STATUS ──
    if len(m.command) == 2 and m.command[1].lower() == "status":
        ch = _dp_channels.get(m.chat.id)
        played_count = len(_dp_played.get(m.chat.id, set()))
        if ch:
            try:
                await m.reply_text(
                    f"📡 <b>DirectPlay Active</b>\n\n"
                    f"Channel ID: <code>{ch}</code>\n"
                    f"Is session mein baje: <b>{played_count}</b> songs"
                )
            except Exception:
                pass
        else:
            try:
                await m.reply_text(
                    "❌ DirectPlay abhi set nahi hai.\n\n"
                    "Use: <code>/directplay &lt;channel_id&gt;</code>"
                )
            except Exception:
                pass
        return

    # ── START ──
    if len(m.command) < 2:
        try:
            await m.reply_text(
                "❓ <b>Usage:</b>\n\n"
                "<code>/directplay &lt;channel_id&gt;</code> — Channel set karo aur bajao\n"
                "<code>/directplay stop</code> — Band karo\n"
                "<code>/directplay status</code> — Status dekho\n\n"
                "<i>Channel ID example: -1001234567890</i>"
            )
        except Exception:
            pass
        return

    raw = m.command[1].strip()

    if raw.lstrip("-").isdigit():
        channel_id = int(raw)
    else:
        try:
            chat = await app.get_chat(raw)
            channel_id = chat.id
        except Exception:
            try:
                await m.reply_text(
                    "❌ <b>Invalid channel!</b>\n\n"
                    "Numeric ID use karo, jaise: <code>-1001234567890</code>"
                )
            except Exception:
                pass
            return

    try:
        ch_info = await app.get_chat(channel_id)
    except (ChannelInvalid, ChannelPrivate):
        try:
            await m.reply_text(
                "❌ <b>Channel access nahi hua!</b>\n\n"
                "Bot ko us channel mein admin banao phir try karo."
            )
        except Exception:
            pass
        return
    except Exception as e:
        try:
            await m.reply_text(f"❌ Channel verify nahi hua: <code>{e}</code>")
        except Exception:
            pass
        return

    _dp_channels[m.chat.id] = channel_id
    _dp_played.pop(m.chat.id, None)
    _dp_ctrl_msg.pop(m.chat.id, None)

    try:
        status_msg = await m.reply_text(
            f"📡 <b>DirectPlay Set!</b>\n\n"
            f"Channel: <b>{ch_info.title}</b>\n"
            f"<code>{channel_id}</code>\n\n"
            f"🔎 Pehla random song dhundh raha hoon..."
        )
    except Exception:
        status_msg = None

    asyncio.create_task(_safe_download_and_play(m.chat.id, status_msg))


# ─────────────────────────────────────────────
#  Callbacks
# ─────────────────────────────────────────────

@app.on_callback_query(filters.regex(r"^dp_next_(-?\d+)$"))
async def directplay_next_cb(_, q: CallbackQuery):
    group_chat_id = int(q.matches[0].group(1))

    if q.message.chat.id != group_chat_id:
        await q.answer("❌ Wrong chat!", show_alert=True)
        return

    if group_chat_id not in _dp_channels:
        await q.answer("⚠️ DirectPlay abhi active nahi hai.", show_alert=True)
        return

    await q.answer("⏭ Next song aa raha hai...")

    try:
        await q.message.edit_reply_markup(
            InlineKeyboardMarkup(
                [[InlineKeyboardButton("⏳ Loading...", callback_data="dp_loading")]]
            )
        )
    except Exception:
        pass

    asyncio.create_task(_safe_download_and_play(group_chat_id, q.message))


@app.on_callback_query(filters.regex(r"^dp_loading$"))
async def dp_loading_cb(_, q: CallbackQuery):
    await q.answer("⏳ Song load ho raha hai, ruko...", show_alert=False)
