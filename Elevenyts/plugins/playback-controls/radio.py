# ==============================================================================
# example_radio.py - Radio Plugin Template
# ==============================================================================
# This is a template file for creating custom radio streaming plugins.
# You can implement your own radio station streaming functionality here.
#
# ==============================================================================


# =======================================================================
# implement your radio plugin here (look at other plugins for reference)
# =======================================================================
"""
radio.py - Telegram Channel Radio Plugin + Stop Handler
=========================================================
/radio <channel_username_or_id> — channel ke audio files randomly stream karo
/radio stop                      — radio band karo
/stop ya /end                    — radio + playback dono band karo
"""

import asyncio
import logging
import os
import random
import time

from pyrogram import enums, errors, filters, types
from pyrogram.errors import ChatSendPlainForbidden, ChatWriteForbidden

from Elevenyts import app, db, lang, queue, tune
from Elevenyts.helpers import Media, can_manage_vc
from Elevenyts.helpers._dataclass import Media

logger = logging.getLogger(__name__)

# ── In-memory Radio State ─────────────────────────────────────────────────────
# chat_id → {"channel": int, "played": set(), "active": bool, "task": Task}
RADIO_STATE: dict[int, dict] = {}


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _clear_radio_state(chat_id: int) -> None:
    """Radio state clear karo agar chal raha ho."""
    state = RADIO_STATE.get(chat_id)
    if state:
        state["active"] = False
        task = state.get("task")
        if task and not task.done():
            task.cancel()
        RADIO_STATE.pop(chat_id, None)


async def _fetch_audio_messages(channel_id) -> list[types.Message]:
    """Channel se saare audio/voice messages fetch karo."""
    msgs = []
    try:
        async for msg in app.get_chat_history(channel_id, limit=500):
            if msg.audio or msg.voice:
                msgs.append(msg)
    except errors.ChannelPrivate:
        pass
    except errors.PeerIdInvalid:
        pass
    except Exception as e:
        logger.error(f"Radio: channel history fetch error: {e}")
    return msgs


async def _download_audio(msg: types.Message) -> str | None:
    """Message se audio download karo, file path return karo."""
    media = msg.audio or msg.voice
    if not media:
        return None

    file_unique_id = getattr(media, "file_unique_id", str(msg.id))
    ext = "ogg"
    if msg.audio:
        fname = getattr(media, "file_name", None) or ""
        ext = fname.rsplit(".", 1)[-1] if "." in fname else "mp3"

    file_path = f"downloads/radio_{file_unique_id}.{ext}"
    if os.path.exists(file_path):
        return file_path

    try:
        await msg.download(file_name=file_path)
        return file_path
    except Exception as e:
        logger.error(f"Radio: download failed for msg {msg.id}: {e}")
        return None


def _make_media(msg: types.Message, file_path: str) -> Media:
    """Message se Media dataclass banao."""
    media = msg.audio or msg.voice
    duration_sec = getattr(media, "duration", 0) or 0
    title = (
        getattr(media, "title", None)
        or getattr(media, "file_name", None)
        or f"Radio Track #{msg.id}"
    )
    if duration_sec >= 3600:
        duration_str = time.strftime("%H:%M:%S", time.gmtime(duration_sec))
    elif duration_sec > 0:
        duration_str = time.strftime("%M:%S", time.gmtime(duration_sec))
    else:
        duration_str = "Unknown"

    return Media(
        id=f"radio_{getattr(media, 'file_unique_id', msg.id)}",
        duration=duration_str,
        duration_sec=duration_sec,
        file_path=file_path,
        message_id=0,
        title=title[:60],
        url=msg.link or "",
        user="📻 Radio",
        is_live=False,
        video=False,
    )


async def _radio_loop(chat_id: int) -> None:
    """Main radio loop — random audio uthao, play karo, repeat."""
    state = RADIO_STATE.get(chat_id)
    if not state:
        return

    channel = state["channel"]
    played: set = state["played"]

    all_msgs = await _fetch_audio_messages(channel)
    if not all_msgs:
        try:
            await app.send_message(chat_id, "❌ <b>Radio:</b> Channel mein koi audio nahi mila.")
        except Exception:
            pass
        RADIO_STATE.pop(chat_id, None)
        return

    while state.get("active"):
        unplayed = [m for m in all_msgs if m.id not in played]
        if not unplayed:
            played.clear()
            fresh = await _fetch_audio_messages(channel)
            if fresh:
                all_msgs = fresh
            unplayed = all_msgs[:]

        chosen: types.Message = random.choice(unplayed)
        played.add(chosen.id)

        file_path = await _download_audio(chosen)
        if not file_path:
            continue

        media = _make_media(chosen, file_path)

        queue.clear(chat_id)
        queue.add(chat_id, media)

        try:
            await app.send_message(
                chat_id,
                f"📻 <b>Radio Playing</b>\n\n"
                f"🎵 <b>{media.title}</b>\n"
                f"⏱ Duration: {media.duration}\n\n"
                f"<i>Next random track aayega automatically…</i>"
            )
        except Exception:
            pass

        try:
            await tune.play_media(chat_id=chat_id, message=None, media=media)
        except Exception as e:
            logger.error(f"Radio: play_media error for {chat_id}: {e}")
            await asyncio.sleep(3)
            continue

        wait_sec = (media.duration_sec + 3) if media.duration_sec else 180

        elapsed = 0
        while elapsed < wait_sec and state.get("active"):
            await asyncio.sleep(2)
            elapsed += 2
            if not await db.get_call(chat_id):
                state["active"] = False
                break

        if not state.get("active"):
            break

    RADIO_STATE.pop(chat_id, None)
    logger.info(f"Radio loop ended for {chat_id}")


# ── /radio Command ────────────────────────────────────────────────────────────

@app.on_message(filters.command("radio") & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def radio_command(_, m: types.Message):
    """/radio <channel> — radio shuru karo | /radio stop — band karo"""
    try:
        await m.delete()
    except Exception:
        pass

    args = m.command[1:]

    # /radio stop
    if args and args[0].lower() == "stop":
        if m.chat.id not in RADIO_STATE:
            try:
                return await m.reply_text("📻 Abhi koi radio chal nahi raha.")
            except Exception:
                return

        _clear_radio_state(m.chat.id)
        await tune.stop(m.chat.id)

        try:
            msg = await m.reply_text(
                f"📻 <b>Radio Band!</b>\n\n{m.from_user.mention} ne radio stop kar diya."
            )
            await asyncio.sleep(5)
            await msg.delete()
        except Exception:
            pass
        return

    # /radio (no args)
    if not args:
        try:
            return await m.reply_text(
                "📻 <b>Radio Usage:</b>\n\n"
                "<code>/radio @channel_username</code> — radio shuru karo\n"
                "<code>/radio stop</code> — radio band karo\n\n"
                "<i>Bot ko channel mein member hona chahiye!</i>"
            )
        except Exception:
            return

    channel_input = args[0].strip()

    # Pehle se chal raha ho toh pehle band karo
    if m.chat.id in RADIO_STATE:
        _clear_radio_state(m.chat.id)
        await tune.stop(m.chat.id)

    sent = None
    try:
        sent = await m.reply_text(f"📻 <b>Radio shuru ho raha hai…</b>\n\nChannel: <code>{channel_input}</code>")
    except Exception:
        pass

    try:
        channel_chat = await app.get_chat(channel_input)
        channel_id = channel_chat.id
    except errors.UsernameNotOccupied:
        if sent:
            try:
                await sent.edit_text(f"❌ Channel <code>{channel_input}</code> nahi mila.")
            except Exception:
                pass
        return
    except errors.PeerIdInvalid:
        if sent:
            try:
                await sent.edit_text(f"❌ Channel ID invalid: <code>{channel_input}</code>")
            except Exception:
                pass
        return
    except Exception as e:
        logger.error(f"Radio: channel resolve error: {e}")
        if sent:
            try:
                await sent.edit_text(f"❌ Channel access error: {type(e).__name__}")
            except Exception:
                pass
        return

    if sent:
        try:
            await sent.delete()
        except Exception:
            pass

    RADIO_STATE[m.chat.id] = {
        "channel": channel_id,
        "played": set(),
        "active": True,
        "task": None,
    }

    task = asyncio.create_task(_radio_loop(m.chat.id))
    RADIO_STATE[m.chat.id]["task"] = task
    logger.info(f"Radio started for chat {m.chat.id} from channel {channel_id}")


# ── /stop & /end Command ──────────────────────────────────────────────────────

@app.on_message(filters.command(["end", "stop"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _stop(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    if len(m.command) > 1:
        return

    if not await db.get_call(m.chat.id):
        try:
            return await m.reply_text(m.lang["not_playing"])
        except (ChatSendPlainForbidden, ChatWriteForbidden):
            return
        except Exception as e:
            logger.error(f"Failed to send reply: {e}")
            return

    # Radio chal raha ho toh uska state bhi clear karo
    _clear_radio_state(m.chat.id)

    await tune.stop(m.chat.id)
    try:
        sent_msg = await m.reply_text(m.lang["play_stopped"].format(m.from_user.mention))
    except (ChatSendPlainForbidden, ChatWriteForbidden):
        return
    except Exception as e:
        logger.error(f"Failed to send stop confirmation: {e}")
        return

    await asyncio.sleep(5)
    try:
        await sent_msg.delete()
    except Exception:
        pass
