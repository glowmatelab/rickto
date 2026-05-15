# Elevenyts/plugins/features/lyrics.py
# Lyrics Fetcher — apis.xditya.me

import aiohttp
import logging
from pyrogram import filters, enums
from pyrogram.types import Message
from Elevenyts import app

logger = logging.getLogger(__name__)

LYRICS_API = "https://apis.xditya.me/lyrics"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /lyrics ᴄᴏᴍᴍᴀɴᴅ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("lyrics") & (filters.group | filters.private))
async def lyrics_cmd(_, message: Message):

    query = " ".join(message.command[1:]).strip()

    if not query:
        await message.reply_text(
            "<blockquote>"
            "⚠️  ꜱᴏɴɢ ɴᴀᴍᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ\n\n"
            "ʜᴏᴡ ᴛᴏ ᴜꜱᴇ :\n"
            "  <code>/lyrics Shape of You</code>\n"
            "  <code>/lyrics Tum Hi Ho</code>"
            "</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    status = await message.reply_text(
        "<blockquote>"
        "🔍  ꜱᴇᴀʀᴄʜɪɴɢ ʟʏʀɪᴄꜱ...\n\n"
        f"🎵  <code>{query}</code>"
        "</blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                LYRICS_API,
                params={"song": query},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:

                if resp.status != 200:
                    await status.edit_text(
                        "<blockquote>"
                        f"❌  ᴀᴘɪ ᴇʀʀᴏʀ  —  <code>{resp.status}</code>"
                        "</blockquote>",
                        parse_mode=enums.ParseMode.HTML,
                    )
                    return

                data = await resp.json()

    except aiohttp.ClientConnectorError:
        await status.edit_text(
            "<blockquote>❌  ᴀᴘɪ ᴜɴʀᴇᴀᴄʜᴀʙʟᴇ. ʙᴀᴅ ᴍᴇ ᴛʀʏ ᴋᴀʀᴏ.</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return
    except aiohttp.ServerTimeoutError:
        await status.edit_text(
            "<blockquote>❌  ʀᴇqᴜᴇꜱᴛ ᴛɪᴍᴇᴏᴜᴛ. ʙᴀᴅ ᴍᴇ ᴛʀʏ ᴋᴀʀᴏ.</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return
    except Exception as e:
        logger.error(f"lyrics fetch error: {e}")
        await status.edit_text(
            f"<blockquote>❌  ᴇʀʀᴏʀ\n\n<code>{e}</code></blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    # ── API response parse ──
    lyrics = (data.get("lyrics") or "").strip()
    name   = (data.get("name")   or query).strip()
    artist = (data.get("artist") or "").strip()

    if not lyrics:
        await status.edit_text(
            "<blockquote>"
            "😔  ʟʏʀɪᴄꜱ ɴᴏᴛ ꜰᴏᴜɴᴅ\n\n"
            f"🎵  <b>{query}</b>\n\n"
            "ᴅɪꜰꜰᴇʀᴇɴᴛ ꜱᴘᴇʟʟɪɴɢ ᴛʀʏ ᴋᴀʀᴏ."
            "</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    # ── header ──
    header = f"🎶  <b>{name}</b>"
    if artist:
        header += f"\n🎤  <i>{artist}</i>"

    # ── expandable blockquote mein lyrics ──
    # Telegram limit: 4096 chars per message
    # expandable blockquote mein sab ek hi message mein aata hai — no spam
    full_text = (
        f"<blockquote>{header}</blockquote>\n"
        f"<blockquote expandable>{lyrics}</blockquote>"
    )

    if len(full_text) <= 4096:
        await status.edit_text(
            full_text,
            parse_mode=enums.ParseMode.HTML,
        )
    else:
        # Bahut lambi lyrics — split karo, har part expandable
        await status.delete()
        chunks = _split_text(lyrics, limit=3800)

        for i, chunk in enumerate(chunks):
            part_header = (
                f"<blockquote>{header}  —  ᴘᴀʀᴛ {i + 1}/{len(chunks)}</blockquote>\n"
                if i > 0 else
                f"<blockquote>{header}</blockquote>\n"
            )
            text = part_header + f"<blockquote expandable>{chunk}</blockquote>"
            await message.reply_text(text, parse_mode=enums.ParseMode.HTML)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ʜᴇʟᴘᴇʀ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _split_text(text: str, limit: int = 3800) -> list[str]:
    """Long lyrics ko line breaks pe split karo."""
    chunks = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit:
            if current:
                chunks.append(current.strip())
            current = line
        else:
            current += line
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text[:limit]]
