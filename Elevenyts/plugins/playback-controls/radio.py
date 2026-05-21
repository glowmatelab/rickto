import asyncio
import logging
import aiohttp
import random

from pyrogram import filters, types

from Elevenyts import app, db, lang, tune
from Elevenyts.helpers import can_manage_vc

logger = logging.getLogger(__name__)

RADIO_STATE: dict[int, dict] = {}

RADIO_API = "https://de1.api.radio-browser.info/json"


async def _search_stations(query: str = None, country: str = None, tag: str = None, limit: int = 10) -> list[dict]:
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
    state = RADIO_STATE.get(chat_id)
    if not state:
        return

    stream_url = station.get("url_resolved") or station.get("url")
    name = station.get("name", "Radio").strip()
    country = station.get("country", "🌐 Unknown")
    tags = station.get("tags", "")
    genre = tags[:40] if tags else "Unknown"
    votes = station.get("votes", 0)
    clickcount = station.get("clickcount", 0)

    try:
        await app.send_message(
            chat_id,
            f"<blockquote>"
            f"📻 <b>Radio Started!</b>"
            f"</blockquote>\n\n"
            f"<blockquote>"
            f"🎙 <b>Station:</b> {name}\n"
            f"🌍 <b>Country:</b> {country}\n"
            f"🎵 <b>Genre:</b> {genre}\n"
            f"👍 <b>Votes:</b> {votes} · 🎧 <b>Plays:</b> {clickcount}"
            f"</blockquote>\n\n"
            f"<blockquote>"
            f"⏹ <i>Use /radio stop to stop the radio</i>"
            f"</blockquote>"
        )
    except:
        pass

    from Elevenyts.helpers import Media

    media = Media(
        id=f"radio_{station.get('stationuuid', 'live')}",
        duration="LIVE",
        duration_sec=0,
        file_path=stream_url,
        message_id=0,
        title=name[:60],
        url=f"https://t.me/{app.username}",  # ← Stream URL ki jagah bot link do
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
            await app.send_message(
                chat_id,
                f"<blockquote>"
                f"❌ <b>Radio Error!</b>\n\n"
                f"Stream load nahi ho saka.\n"
                f"<code>{e}</code>\n\n"
                f"Doosra station try karo: /radio {genre}"
                f"</blockquote>"
            )
        except:
            pass
        return

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

    if args and args[0].lower() == "stop":
        if m.chat.id not in RADIO_STATE:
            return await m.reply_text(
                "<blockquote>📻 <b>Radio</b>\n\nAbhi koi radio nahi chal raha.</blockquote>"
            )
        _clear_radio_state(m.chat.id)
        await tune.stop(m.chat.id)
        return await m.reply_text(
            "<blockquote>⏹ <b>Radio Stopped!</b>\n\nRadio band kar diya gaya.</blockquote>"
        )

    if not args:
        return await m.reply_text(
            "<blockquote>"
            "📻 <b>Radio — Usage</b>"
            "</blockquote>\n\n"
            "<blockquote>"
            "🎵 <b>Genre se search:</b>\n"
            "<code>/radio bollywood</code> — Bollywood\n"
            "<code>/radio hindi</code> — Hindi\n"
            "<code>/radio jazz</code> — Jazz\n"
            "<code>/radio lofi</code> — Lo-Fi\n"
            "<code>/radio pop</code> — Pop\n"
            "<code>/radio classical</code> — Classical"
            "</blockquote>\n\n"
            "<blockquote>"
            "⏹ <code>/radio stop</code> — Radio band karo\n\n"
            "<i>Koi bhi genre ya station naam likho!</i>"
            "</blockquote>"
        )

    query = " ".join(args).strip()

    if m.chat.id in RADIO_STATE:
        _clear_radio_state(m.chat.id)
        await tune.stop(m.chat.id)

    status = await m.reply_text(
        f"<blockquote>🔍 <b>Searching...</b>\n\n<i>{query}</i> ke liye stations dhundh raha hoon...</blockquote>"
    )

    stations = await _search_stations(tag=query, limit=20)
    if not stations:
        stations = await _search_stations(query=query, limit=20)

    if not stations:
        return await status.edit(
            f"<blockquote>"
            f"❌ <b>Station Nahi Mila!</b>\n\n"
            f"<i>{query}</i> ke liye koi station nahi mila.\n"
            f"Doosra genre try karo jaise: <code>hindi</code>, <code>bollywood</code>, <code>lofi</code>"
            f"</blockquote>"
        )

    station = random.choice(stations)
    await status.delete()

    RADIO_STATE[m.chat.id] = {
        "active": True,
        "task": None,
        "station": station,
    }

    task = asyncio.create_task(_radio_loop(m.chat.id, station))
    RADIO_STATE[m.chat.id]["task"] = task
