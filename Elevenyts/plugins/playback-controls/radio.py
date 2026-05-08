# ==============================================================================
# radio.py - Telegram Channel Radio Plugin
# ==============================================================================

import asyncio
import logging
import os
import random
import time

from pyrogram import enums, errors, filters, types
from pyrogram.errors import ChatSendPlainForbidden, ChatWriteForbidden

# 'assistant' ya 'user' client ko import karein (aapke framework ke naam ke hisaab se)
from Elevenyts import app, assistant, db, lang, queue, tune
from Elevenyts.helpers import Media, can_manage_vc

logger = logging.getLogger(__name__)

# ── Radio State ──────────────────────────────────────────────────────────────
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
    """
    Bot ki jagah Assistant use karein taaki 
    BOT_METHOD_INVALID error na aaye.
    """
    msgs = []
    try:
        # Yahan 'assistant' ka use ho raha hai history fetch karne ke liye
        async for msg in assistant.get_chat_history(channel_id, limit=500):
            if msg.audio or msg.voice:
                msgs.append(msg)
    except Exception as e:
        logger.error(f"Radio: History fetch error: {e}")
    return msgs


async def _download_audio(msg: types.Message) -> str | None:
    """Message se audio download karo."""
    media = msg.audio or msg.voice
    if not media:
        return None

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    file_unique_id = getattr(media, "file_unique_id", str(msg.id))
    ext = "mp3"
    if msg.audio:
        fname = getattr(media, "file_name", "") or ""
        ext = fname.rsplit(".", 1)[-1] if "." in fname else "mp3"
    elif msg.voice:
        ext = "ogg"

    file_path = f"downloads/radio_{file_unique_id}.{ext}"
    if os.path.exists(file_path):
        return file_path

    try:
        # Assistant se download karwana zyada fast aur reliable hota hai
        await assistant.download_media(msg, file_name=file_path)
        return file_path
    except Exception as e:
        logger.error(f"Radio: download failed: {e}")
        return None


def _make_media(msg: types.Message, file_path: str) -> Media:
    """Media dataclass object banayein."""
    media = msg.audio or msg.voice
    duration_sec = getattr(media, "duration", 0) or 0
    title = (
        getattr(media, "title", None)
        or getattr(media, "file_name", None)
        or f"Radio Track #{msg.id}"
    )
    
    if duration_sec >= 3600:
        duration_str = time.strftime("%H:%M:%S", time.gmtime(duration_sec))
    else:
        duration_str = time.strftime("%M:%S", time.gmtime(duration_sec))

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
    """Main radio loop."""
    state = RADIO_STATE.get(chat_id)
    if not state:
        return

    channel = state["channel"]
    played: set = state["played"]

    all_msgs = await _fetch_audio_messages(channel)
    if not all_msgs:
        try:
            await app.send_message(chat_id, "❌ <b>Radio:</b> Channel mein koi audio nahi mila ya Assistant channel mein nahi hai.")
        except: pass
        RADIO_STATE.pop(chat_id, None)
        return

    while state.get("active"):
        unplayed = [m for m in all_msgs if m.id not in played]
        if not unplayed:
            played.clear()
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
                f"<i>Auto-playing next track from channel...</i>"
            )
        except: pass

        try:
            await tune.play_media(chat_id=chat_id, message=None, media=media)
        except Exception as e:
            logger.error(f"Radio: play_media error: {e}")
            await asyncio.sleep(5)
            continue

        # Wait loop
        wait_sec = (media.duration_sec + 2) if media.duration_sec else 180
        elapsed = 0
        while elapsed < wait_sec and state.get("active"):
            await asyncio.sleep(2)
            elapsed += 2
            if not await db.get_call(chat_id):
                state["active"] = False
                break

    RADIO_STATE.pop(chat_id, None)


# ── Commands ──────────────────────────────────────────────────────────────────

@app.on_message(filters.command("radio") & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def radio_command(_, m: types.Message):
    args = m.command[1:]

    if args and args[0].lower() == "stop":
        if m.chat.id not in RADIO_STATE:
            return await m.reply_text("📻 Abhi koi radio nahi chal raha.")
        _clear_radio_state(m.chat.id)
        await tune.stop(m.chat.id)
        return await m.reply_text("📻 Radio stop kar diya gaya.")

    if not args:
        return await m.reply_text("📻 <b>Usage:</b> <code>/radio @channel</code>")

    channel_input = args[0].strip()
    
    # Existing radio stop karo
    if m.chat.id in RADIO_STATE:
        _clear_radio_state(m.chat.id)
        await tune.stop(m.chat.id)

    try:
        # Chat info nikalne ke liye assistant use karna better hai
        channel_chat = await assistant.get_chat(channel_input)
        channel_id = channel_chat.id
    except Exception as e:
        return await m.reply_text(f"❌ Error: {e}")

    RADIO_STATE[m.chat.id] = {
        "channel": channel_id,
        "played": set(),
        "active": True,
        "task": None,
    }

    task = asyncio.create_task(_radio_loop(m.chat.id))
    RADIO_STATE[m.chat.id]["task"] = task
    await m.reply_text(f"📻 <b>Radio Started!</b>\n\nChannel: <code>{channel_chat.title}</code>")


@app.on_message(filters.command(["end", "stop"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _stop_all(_, m: types.Message):
    _clear_radio_state(m.chat.id)
    await tune.stop(m.chat.id)
    try:
        await m.reply_text("🛑 Playback and Radio stopped.")
    except: pass
