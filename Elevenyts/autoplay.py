import asyncio
from pyrogram import filters
from py_yt import VideosSearch
# Humne 'call' ko hata diya hai kyunki wo error de raha tha
from Elevenyts import app, db, logger, youtube, queue, tune, tasks
from Elevenyts.helpers import Track, utils

# --- 1. DATABASE HELPERS ---
async def set_ap_status(chat_id, status: bool):
    await db.cache.update_one({"_id": f"autoplay_{chat_id}"}, {"$set": {"status": status}}, upsert=True)

async def get_ap_status(chat_id):
    doc = await db.cache.find_one({"_id": f"autoplay_{chat_id}"})
    return doc.get("status", False) if doc else False

async def set_last_track(chat_id, video_id):
    await db.cache.update_one({"_id": f"last_{chat_id}"}, {"$set": {"video_id": video_id}}, upsert=True)

async def get_last_track(chat_id):
    doc = await db.cache.find_one({"_id": f"last_{chat_id}"})
    return doc.get("video_id") if doc else None

# --- 2. YOUTUBE RELATED SEARCH ---
async def fetch_related(video_id):
    try:
        # Hum seedha ID use karke related videos fetch kar rahe hain
        search = VideosSearch(f"https://www.youtube.com/watch?v={video_id}", limit=2)
        res = await search.next()
        if res and len(res["result"]) > 1:
            data = res["result"][1]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration", "0")),
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                is_live=False,
                video=False,
                message_id=0
            )
    except Exception as e:
        logger.error(f"Autoplay Search Error: {e}")
        return None

# --- 3. THE AUTOPLAY WATCHER (Background Task) ---
async def autoplay_watcher():
    """Checks every 10 seconds if a chat needs a new song via Autoplay."""
    await asyncio.sleep(15) # Wait for bot to fully boot
    logger.info("✨ Autoplay Watcher is now active!")
    
    while True:
        await asyncio.sleep(10)
        # db.active_calls aapke bot ki active chats ki list hai
        for chat_id in list(db.active_calls):
            try:
                # Agar current queue khali hai
                if not queue.get_current(chat_id):
                    # Aur agar us chat mein Autoplay ON hai
                    if await get_ap_status(chat_id):
                        last_id = await get_last_track(chat_id)
                        if last_id:
                            track = await fetch_related(last_id)
                            if track:
                                logger.info(f"🤖 Autoplay: Picking next song for {chat_id}")
                                await set_last_track(chat_id, track.id)
                                # Hum 'tune.play_track' use karenge 'call' ki jagah
                                await tune.play_track(chat_id, track)
            except Exception as e:
                pass # Silent ignore to keep loop running

# --- 4. COMMAND HANDLER (/aplay) ---
@app.on_message(filters.command("aplay") & filters.group)
async def aplay_handler(_, message):
    chat_id = message.chat.id
    
    # Toggle OFF: /aplay off
    if len(message.command) > 1 and message.command[1].lower() == "off":
        await set_ap_status(chat_id, False)
        return await message.reply_text("🛑 **Autoplay Mode:** Disabled.")

    query = " ".join(message.command[1:])
    if not query:
        return await message.reply_text("✨ **Usage:** `/aplay [song name]`")

    m = await message.reply_text("🔎 Searching...")
    
    # Existing youtube search helper
    track = await youtube.search(query, message.id)
    if not track:
        return await m.edit("❌ Song not found.")

    # Enable Autoplay settings
    await set_ap_status(chat_id, True)
    await set_last_track(chat_id, track.id)
    
    # Start playback
    await tune.play_track(chat_id, track)
    await m.edit(f"✅ **Autoplay ON**\n🎵 **Playing:** {track.title}")

# --- 5. REGISTER TASK ---
tasks.append(asyncio.create_task(autoplay_watcher()))
