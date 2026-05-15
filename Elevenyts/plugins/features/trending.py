# Elevenyts/plugins/features/trending_recommend.py
# YouTube Music Trending + Recommend

import logging
from pyrogram import filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from ytmusicapi import YTMusic
from Elevenyts import app

logger = logging.getLogger(__name__)

_ytm = YTMusic()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ʜᴇʟᴘᴇʀꜱ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get_trending(limit: int = 10) -> list[dict]:
    """India ke top trending songs fetch karo."""
    try:
        charts = _ytm.get_charts(country="IN")
        items = charts.get("songs", {}).get("items", [])
        result = []
        for item in items[:limit]:
            title   = item.get("title", "Unknown")
            artists = ", ".join(a["name"] for a in item.get("artists", []))
            vid_id  = item.get("videoId", "")
            views   = item.get("views", "")
            result.append({
                "title":   title,
                "artists": artists,
                "videoId": vid_id,
                "views":   views,
            })
        return result
    except Exception as e:
        logger.error(f"trending fetch error: {e}")
        return []


def _get_recommendations(query: str, limit: int = 8) -> list[dict]:
    """Song name se similar songs fetch karo."""
    try:
        results = _ytm.search(query, filter="songs", limit=1)
        if not results:
            return []

        video_id = results[0].get("videoId")
        if not video_id:
            return []

        # related songs via watch playlist
        watch = _ytm.get_watch_playlist(videoId=video_id, limit=limit + 1)
        tracks = watch.get("tracks", [])[1:limit + 1]  # skip first (same song)

        recs = []
        for t in tracks:
            title   = t.get("title", "Unknown")
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            vid_id  = t.get("videoId", "")
            recs.append({
                "title":   title,
                "artists": artists,
                "videoId": vid_id,
            })
        return recs
    except Exception as e:
        logger.error(f"recommend fetch error: {e}")
        return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /trending ᴄᴏᴍᴍᴀɴᴅ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("trending") & (filters.group | filters.private))
async def trending_cmd(_, message: Message):

    status = await message.reply_text(
        "<blockquote>📊  ꜰᴇᴛᴄʜɪɴɢ ᴛʀᴇɴᴅɪɴɢ...</blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )

    songs = _get_trending(limit=10)

    if not songs:
        await status.edit_text(
            "<blockquote>❌  ᴛʀᴇɴᴅɪɴɢ ꜰᴇᴛᴄʜ ꜰᴀɪʟᴇᴅ. ʙᴀᴀᴅ ᴍᴇ ᴛʀʏ ᴋᴀʀᴏ.</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    lines = []
    buttons = []
    for i, s in enumerate(songs, 1):
        lines.append(
            f"  <b>{i}.</b>  {s['title']}\n"
            f"       <i>{s['artists']}</i>"
            + (f"\n       👁  {s['views']}" if s['views'] else "")
        )
        if s["videoId"]:
            buttons.append([
                InlineKeyboardButton(
                    f"{i}. {s['title'][:30]}",
                    url=f"https://www.youtube.com/watch?v={s['videoId']}",
                )
            ])

    text = (
        "<blockquote>"
        "🔥  ᴛʀᴇɴᴅɪɴɢ  —  🇮🇳 ɪɴᴅɪᴀ\n\n"
        + "\n\n".join(lines)
        + "\n</blockquote>"
    )

    await status.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /recommend ᴄᴏᴍᴍᴀɴᴅ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("recommend") & (filters.group | filters.private))
async def recommend_cmd(_, message: Message):

    query = " ".join(message.command[1:]).strip()

    if not query:
        await message.reply_text(
            "<blockquote>"
            "⚠️  ꜱᴏɴɢ ɴᴀᴍᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ\n\n"
            "ʜᴏᴡ ᴛᴏ ᴜꜱᴇ :\n"
            "  <code>/recommend Tum Hi Ho</code>\n"
            "  <code>/recommend Shape of You</code>"
            "</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    status = await message.reply_text(
        "<blockquote>"
        f"🎯  ꜰɪɴᴅɪɴɢ ꜱɪᴍɪʟᴀʀ ꜱᴏɴɢꜱ...\n\n"
        f"🎵  <code>{query}</code>"
        "</blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )

    songs = _get_recommendations(query, limit=8)

    if not songs:
        await status.edit_text(
            "<blockquote>"
            "😔  ᴄᴏɪ ꜱɪᴍɪʟᴀʀ ꜱᴏɴɢ ɴᴀʜɪ ᴍɪʟᴀ\n\n"
            "ᴅɪꜰꜰᴇʀᴇɴᴛ ꜱᴏɴɢ ɴᴀᴍᴇ ᴛʀʏ ᴋᴀʀᴏ."
            "</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    lines = []
    buttons = []
    for i, s in enumerate(songs, 1):
        lines.append(
            f"  <b>{i}.</b>  {s['title']}\n"
            f"       <i>{s['artists']}</i>"
        )
        if s["videoId"]:
            buttons.append([
                InlineKeyboardButton(
                    f"{i}. {s['title'][:30]}",
                    url=f"https://www.youtube.com/watch?v={s['videoId']}",
                )
            ])

    text = (
        "<blockquote>"
        f"🎯  ꜱɪᴍɪʟᴀʀ ᴛᴏ  —  <b>{query}</b>\n\n"
        + "\n\n".join(lines)
        + "\n</blockquote>"
    )

    await status.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
    )
