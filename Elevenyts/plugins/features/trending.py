# Elevenyts/plugins/features/trending_recommend.py
# YouTube Music Trending + Recommend

import asyncio
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

async def _get_trending(limit: int = 10) -> list[dict]:
    try:
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            "--no-warnings",
            "--playlist-end", str(limit),
            "https://music.youtube.com/playlist?list=PLrEnWoR732-BHrPp_Pm8_VleD68f9s14-",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)

        import json
        result = []
        for line in stdout.decode().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                title    = d.get("title", "Unknown")
                uploader = d.get("uploader") or d.get("channel") or ""
                vid_id   = d.get("id") or d.get("url", "").split("v=")[-1]
                result.append({
                    "title":   title,
                    "artists": uploader,
                    "videoId": vid_id,
                })
            except Exception:
                continue
        return result

    except asyncio.TimeoutError:
        logger.error("trending timeout")
        return []
    except Exception as e:
        logger.error(f"trending error: {e}")
        return []


def _get_recommendations(query: str, limit: int = 8) -> list[dict]:
    try:
        results = _ytm.search(query, filter="songs", limit=1)
        if not results:
            return []

        video_id = results[0].get("videoId")
        if not video_id:
            return []

        watch  = _ytm.get_watch_playlist(videoId=video_id, limit=limit + 1)
        tracks = watch.get("tracks", [])[1:limit + 1]

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
        logger.error(f"recommend error: {e}")
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

    songs = await _get_trending(limit=10)

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
            f"  <b>{i}.</b>  {s['title']}"
            + (f"\n       <i>{s['artists']}</i>" if s['artists'] else "")
        )
        if s["videoId"]:
            buttons.append([
                InlineKeyboardButton(
                    f"{i}. {s['title'][:35]}",
                    url=f"https://www.youtube.com/watch?v={s['videoId']}",
                )
            ])

    body = "\n\n".join(lines)

    text = (
        "<blockquote>🔥  ᴛʀᴇɴᴅɪɴɢ  —  🇮🇳 ɪɴᴅɪᴀ</blockquote>\n"
        f"<blockquote expandable>{body}</blockquote>"
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

    songs = await asyncio.get_event_loop().run_in_executor(
        None, _get_recommendations, query, 8
    )

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
                    f"{i}. {s['title'][:35]}",
                    url=f"https://www.youtube.com/watch?v={s['videoId']}",
                )
            ])

    body = "\n\n".join(lines)

    text = (
        f"<blockquote>🎯  ꜱɪᴍɪʟᴀʀ ᴛᴏ  —  <b>{query}</b></blockquote>\n"
        f"<blockquote expandable>{body}</blockquote>"
    )

    await status.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
    )
