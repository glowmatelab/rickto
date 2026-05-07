import asyncio
from pyrogram import filters
from py_yt import VideosSearch
from Elevenyts import app, db, logger, youtube, queue, tune
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
                thumbnail=data.get("thumbnails", [{}])[-1].get("url"),
                url=data.get("link"),
                is_live=False,
                video=False,
                message_id=0 # Autoplayed songs don't have a trigger msg
            )
    except: return None

# --- 3. THE AUTOPLAY WATCHER (Background Task) ---
async def autoplay_watcher():
    """
    Har 10 second mein check karega ki kya koi chat khali hai 
    aur wahan autoplay ON hai.
    """
    logger.info("✨ Autoplay Watcher Started!")
    while True:
        await asyncio.sleep(10)
        for chat_id in list(db.active_calls):
            try:
                # Check if queue is empty
                if not queue.get_current(chat_id):
                    # Check if autoplay is ON
                    if await get_ap_status(chat_id):
                        last_id = await get_last_track(chat_id)
                        if last_id:
                            track = await fetch_related(last_id)
                            if track:
                                logger.info(f"🤖 Autoplay: Playing related song in {chat_id}")
                                await set_last_track(chat_id, track.id)
                                await tune.play_track(chat_id, track)
            except Exception as e:
                logger.error(f"Autoplay Watcher Error: {e}")

# --- 4. COMMAND HANDLER ---
@app.on_message(filters.command("aplay") & filters.group)
async def aplay_handler(_, message):
    chat_id = message.chat.id
    if len(message.command) > 1 and message.command[1].lower() == "off":
        await set_ap_status(chat_id, False)
        return await message.reply_text("🛑 **Autoplay OFF**")

    query = " ".join(message.command[1:])
    if not query: return await message.reply_text("✨ `/aplay [song name]`")

    m = await message.reply_text("🔎 Searching...")
    track = await youtube.search(query, message.id)
    if not track: return await m.edit("❌ Not found")

    await set_ap_status(chat_id, True)
    await set_last_track(chat_id, track.id)
    
    await tune.play_track(chat_id, track)
    await m.edit(f"✅ **Autoplay ON**\n🎵 **Playing:** {track.title}")

# --- 5. REGISTER THE TASK ---
from Elevenyts import tasks
tasks.append(asyncio.create_task(autoplay_watcher()))
