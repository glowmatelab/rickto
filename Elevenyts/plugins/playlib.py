# =========================================
# FILE:
# Elevenyts/plugins/playlib.py
# =========================================

import os
import random

from pyrogram import filters
from pyrogram.types import Message
from pytgcalls.types import MediaStream
from pytgcalls.types.stream import StreamAudioEnded

from Elevenyts import app, call


# =========================================
# SETTINGS
# =========================================

LIBRARY_CHANNEL = -100xxxxxxxxxx
# apna channel id daalo


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

    async for msg in app.get_chat_history(
        LIBRARY_CHANNEL,
        limit=1000
    ):

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

    song = await app.get_messages(
        LIBRARY_CHANNEL,
        msg_id
    )

    file_path = await song.download()

    old = CURRENT_FILE.get(chat_id)

    if old and os.path.exists(old):
        try:
            os.remove(old)
        except:
            pass

    CURRENT_FILE[chat_id] = file_path

    await call.change_stream(
        chat_id,
        MediaStream(file_path),
    )


# =========================================
# START RADIO
# =========================================

@app.on_message(
    filters.command("playlib")
    & filters.group
)
async def playlib(_, message: Message):

    chat_id = message.chat.id

    LIB_MODE[chat_id] = True

    status = await message.reply_text(
        "📻 Starting Library Radio..."
    )

    if not SONG_CACHE:
        await load_library()

    if not SONG_CACHE:
        return await status.edit(
            "❌ No songs found in library"
        )

    msg_id = random.choice(SONG_CACHE)

    song = await app.get_messages(
        LIBRARY_CHANNEL,
        msg_id
    )

    file_path = await song.download()

    CURRENT_FILE[chat_id] = file_path

    title = (
        song.audio.title
        or song.audio.file_name
        or "Library Song"
    )

    try:

        await call.join_group_call(
            chat_id,
            MediaStream(file_path),
        )

        await status.edit(
            f"📻 Radio Started\n\n🎵 {title}"
        )

    except Exception as e:

        await status.edit(
            f"❌ Error:\n{e}"
        )


# =========================================
# STOP RADIO
# =========================================

@app.on_message(
    filters.command("stoplib")
    & filters.group
)
async def stoplib(_, message: Message):

    chat_id = message.chat.id

    LIB_MODE[chat_id] = False

    try:
        await call.leave_group_call(chat_id)
    except:
        pass

    old = CURRENT_FILE.get(chat_id)

    if old and os.path.exists(old):
        try:
            os.remove(old)
        except:
            pass

    await message.reply_text(
        "⏹ Radio Stopped"
    )


# =========================================
# SKIP SONG
# =========================================

@app.on_message(
    filters.command("skiplib")
    & filters.group
)
async def skiplib(_, message: Message):

    chat_id = message.chat.id

    if not LIB_MODE.get(chat_id):
        return await message.reply_text(
            "❌ Radio not active"
        )

    await play_random(chat_id)

    await message.reply_text(
        "⏭ Next Random Song"
    )


# =========================================
# AUTO NEXT SONG
# =========================================

@call.on_update()
async def stream_end(_, update):

    if isinstance(update, StreamAudioEnded):

        chat_id = update.chat_id

        if LIB_MODE.get(chat_id):

            try:
                await play_random(chat_id)
            except Exception as e:
                print(e)
