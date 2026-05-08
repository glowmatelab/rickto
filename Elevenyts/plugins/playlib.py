# =========================================
# FILE:
# Elevenyts/plugins/playlib.py
# =========================================

import os
import random

from pyrogram import filters
from pyrogram.types import Message

from Elevenyts import app
from pytgcalls import StreamType
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types import Update
from pytgcalls.types.stream import StreamAudioEnded


# =========================================
# SETTINGS
# =========================================

LIBRARY_CHANNEL = -1003956796095
# replace with your channel id


# =========================================
# GLOBALS
# =========================================

SONG_CACHE = []
LIB_MODE = {}
CURRENT_FILE = {}


# =========================================
# LOAD SONGS
# =========================================

async def load_library():
    SONG_CACHE.clear()

    async for msg in app.get_chat_history(LIBRARY_CHANNEL, limit=1000):
        if msg.audio:
            SONG_CACHE.append(msg.id)

    print(f"Loaded {len(SONG_CACHE)} songs")


# =========================================
# PLAY RANDOM SONG
# =========================================

async def play_random(chat_id):

    if not SONG_CACHE:
        await load_library()

    if not SONG_CACHE:
        return

    msg_id = random.choice(SONG_CACHE)

    song = await app.get_messages(LIBRARY_CHANNEL, msg_id)

    file_path = await song.download()

    # delete previous temp file
    old = CURRENT_FILE.get(chat_id)
    if old and os.path.exists(old):
        try:
            os.remove(old)
        except:
            pass

    CURRENT_FILE[chat_id] = file_path

    await app.call_py.change_stream(
        chat_id,
        AudioPiped(file_path),
    )


# =========================================
# START RADIO
# =========================================

@app.on_message(filters.command("playlib") & filters.group)
async def start_radio(_, message: Message):

    chat_id = message.chat.id

    LIB_MODE[chat_id] = True

    status = await message.reply_text("📻 Starting Library Radio...")

    if not SONG_CACHE:
        await load_library()

    if not SONG_CACHE:
        return await status.edit_text("❌ No songs found")

    msg_id = random.choice(SONG_CACHE)

    song = await app.get_messages(LIBRARY_CHANNEL, msg_id)

    file_path = await song.download()

    CURRENT_FILE[chat_id] = file_path

    title = (
        song.audio.title
        or song.audio.file_name
        or "Library Song"
    )

    try:

        await app.call_py.join_group_call(
            chat_id,
            AudioPiped(file_path),
            stream_type=StreamType().local_stream,
        )

        await status.edit_text(
            f"📻 Library Radio Started\n\n🎵 {title}"
        )

    except Exception as e:

        await status.edit_text(f"❌ Error:\n{e}")


# =========================================
# STOP RADIO
# =========================================

@app.on_message(filters.command("stoplib") & filters.group)
async def stop_radio(_, message: Message):

    chat_id = message.chat.id

    LIB_MODE[chat_id] = False

    try:
        await app.call_py.leave_group_call(chat_id)
    except:
        pass

    old = CURRENT_FILE.get(chat_id)

    if old and os.path.exists(old):
        try:
            os.remove(old)
        except:
            pass

    await message.reply_text("⏹ Library Radio Stopped")


# =========================================
# SKIP SONG
# =========================================

@app.on_message(filters.command("skiplib") & filters.group)
async def skip_radio(_, message: Message):

    chat_id = message.chat.id

    if not LIB_MODE.get(chat_id):
        return await message.reply_text("❌ Library mode not active")

    await play_random(chat_id)

    await message.reply_text("⏭ Playing Next Random Song")


# =========================================
# AUTO NEXT SONG
# =========================================

@app.call_py.on_update()
async def stream_end_handler(_, update: Update):

    if isinstance(update, StreamAudioEnded):

        chat_id = update.chat_id

        if LIB_MODE.get(chat_id):

            try:
                await play_random(chat_id)
            except Exception as e:
                print(e)
