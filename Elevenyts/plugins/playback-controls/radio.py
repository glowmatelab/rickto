import asyncio
import logging
import aiohttp
import random

from pyrogram import filters, types
from pyrogram.errors import ChatSendPlainForbidden, ChatWriteForbidden

from Elevenyts import app, db, lang, tune
from Elevenyts.helpers import can_manage_vc

logger = logging.getLogger(__name__)

RADIO_STATE: dict[int, dict] = {}

RADIO_API = "https://de1.api.radio-browser.info/json"


async def _search_stations(query: str = None, country: str = None, tag: str = None, limit: int = 10) -> list[dict]:
    """Radio Browser API se stations dhundo."""
    try:
        params = {
            "limit": limit,
            "hidebroken": "true",
            "order": "clickcount",
            "reverse": "true",
        }
        if query:
            params["name"] = query
        if country:
            params["country"] = country
        if tag:
            params["tag"] = tag

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{RADIO_API}/stations/search",
                params=params,
                headers={"User-Agent": "MusicBot/1.0"}
            ) as resp:
                if resp.status != 200:
                    return []
                return await resp.json()
    except Exception as e:
        logger.error(f"Radio API error: {e}")
        return []


def _clear_radio_state(chat_id: int) -> None:
    state = RADIO_STATE.get(chat_id)
    if state:
        state["active"] = False
        task = state.get("task")
        if task and not task.done():
            task.cancel()
        RADIO_STATE.pop(chat_id, None)


async def _radio_loop(chat_id: int, station: dict) -> None:
    """Radio stream bajao."""
    state = RADIO_STATE.get(chat_id)
    if not state:
        return

    stream_url = station.get("url_resolved") or station.get("url")
    name = station.get("name", "Radio")
    country = station.get("country", "")
    tags = station.get("tags", "")

    try:
        await app.send_message(
            chat_id,
            f"📻 **Radio Started!**\n\n"
            f"🎙 **Station:** {name}\n"
            f"🌍 **Country:** {country}\n"
            f"🎵 **Genre:** {tags[:50] if tags else 'Unknown'}\n\n"
            f"_Use /radio stop to stop_"
        )
    except:
        pass

    from Elevenyts.helpers import Media
    import time

    media = Media(
        id=f"radio_{station.get('stationuuid', 'live')}",
        duration="LIVE",
        duration_sec=0,
        file_path=stream_url,
        message_id=0,
        title=name[:60],
        url=stream_url,
        user="📻 Radio",
        is_live=True,
        video=False,
    )

    try:
        await tune.play_media(chat_id=chat_id, message=None, media=media)
    except Exception as e:
        logger.error(f"Radio play error: {e}")
        _clear_radio_state(chat_id)
        try:
            await app.send_message(chat_id, f"❌ Radio stream error: {e}")
        except:
            pass
        return

    # Active rahne tak wait karo
    while state.get("active"):
        await asyncio.sleep(5)
        if not await db.get_call(chat_id):
            state["active"] = False
            break

    RADIO_STATE.pop(chat_id, None)


@app.on_message(filters.command("radio") & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def radio_command(_, m: types.Message):
    args = m.command[1:]

    # Stop command
    if args and args[0].lower() == "stop":
        if m.chat.id not in RADIO_STATE:
            return await m.reply_text("📻 Abhi koi radio nahi chal raha.")
        _clear_radio_state(m.chat.id)
        await tune.stop(m.chat.id)
        return await m.reply_text("📻 Radio stop kar diya.")

    # Usage
    if not args:
        return await m.reply_text(
            "📻 **Radio Usage:**\n\n"
            "`/radio bollywood` — Bollywood stations\n"
            "`/radio hindi` — Hindi stations\n"
            "`/radio jazz` — Jazz stations\n"
            "`/radio pop` — Pop stations\n"
            "`/radio stop` — Radio band karo\n\n"
            "Koi bhi genre ya station naam likho!"
        )

    query = " ".join(args).strip()

    # Existing radio stop karo
    if m.chat.id in RADIO_STATE:
        _clear_radio_state(m.chat.id)
        await tune.stop(m.chat.id)

    status = await m.reply_text(f"🔍 **{query}** ke liye radio stations dhundh raha hoon...")

    # Stations search karo
    stations = await _search_stations(tag=query, limit=20)
    if not stations:
        stations = await _search_stations(query=query, limit=20)

    if not stations:
        return await status.edit(f"❌ **{query}** ke liye koi station nahi mila!")

    # Random station choose karo
    station = random.choice(stations)

    await status.delete()

    RADIO_STATE[m.chat.id] = {
        "active": True,
        "task": None,
        "station": station,
    }

    task = asyncio.create_task(_radio_loop(m.chat.id, station))
    RADIO_STATE[m.chat.id]["task"] = task
