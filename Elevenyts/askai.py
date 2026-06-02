# Elevenyts/plugins/features/askai.py
# AI Ask — apifreellm.com (20 sec cooldown per user)

import time
import aiohttp
import logging
from pyrogram import filters, enums
from pyrogram.types import Message
from Elevenyts import app
from Elevenyts import config

logger = logging.getLogger(__name__)

ASKAI_API   = "https://apifreellm.com/api/v1/chat"   
COOLDOWN    = 20  # seconds
ASKAI_TOKEN = config.ASKAI_API_KEY
# ── in-memory cooldown store: {user_id: last_used_timestamp} ──
_cooldowns: dict[int, float] = {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /askai ᴄᴏᴍᴍᴀɴᴅ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("askai") & (filters.group | filters.private))
async def askai_cmd(_, message: Message):
    user_id = message.from_user.id

    question = " ".join(message.command[1:]).strip()

    if not question:
        await message.reply_text(
            "<blockquote>"
            "🤖  <b>ᴀsᴋ ᴀɪ</b>\n\n"
            "⚠️  ꜱᴏᴍᴇᴛʜɪɴɢ ᴛᴏ ᴀsᴋ ᴍᴜᴊʜᴇ ʙᴛᴀ?\n\n"
            "ʜᴏᴡ ᴛᴏ ᴜsᴇ :\n"
            "  <code>/askai What is AI?</code>\n"
            "  <code>/askai Python kya hota hai?</code>"
            "</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    # ── cooldown check ──
    now = time.time()
    last_used = _cooldowns.get(user_id, 0)
    remaining = COOLDOWN - (now - last_used)

    if remaining > 0:
        secs = int(remaining) + 1
        await message.reply_text(
            "<blockquote>"
            f"⏳  ʏᴀᴀʀ ᴢʀᴀ ʀᴜᴋ!  <b>{secs}s</b> ʙᴀᴀᴅ ᴘᴜᴄʜʜ.\n\n"
            "🔁  ʜᴀʀ ꜱᴀᴡᴀʟ ᴋᴇ ʙᴀᴀᴅ <b>20 ꜱᴇᴄ</b> ᴋᴀ ᴄᴏᴏʟᴅᴏᴡɴ ʜᴀɪ."
            "</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    # ── mark cooldown ──
    _cooldowns[user_id] = now

    status = await message.reply_text(
        "<blockquote>"
        "🤖  <b>ᴀɪ ꜱᴏᴄʜ ʀᴀʜᴀ ʜᴀɪ...</b>\n\n"
        f"❓  <code>{question}</code>"
        "</blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ASKAI_API,
                headers={
                    "Content-Type":  "application/json",
                    "Authorization": f"Bearer {ASKAI_TOKEN}",
                },
                json={"message": question},
                timeout=aiohttp.ClientTimeout(total=30),
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
            "<blockquote>❌  ᴀᴘɪ ᴜɴʀᴇᴀᴄʜᴀʙʟᴇ. ʙᴀᴀᴅ ᴍᴇ ᴛʀʏ ᴋᴀʀᴏ.</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return
    except aiohttp.ServerTimeoutError:
        await status.edit_text(
            "<blockquote>❌  ʀᴇqᴜᴇꜱᴛ ᴛɪᴍᴇᴏᴜᴛ. ʙᴀᴀᴅ ᴍᴇ ᴛʀʏ ᴋᴀʀᴏ.</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return
    except Exception as e:
        logger.error(f"askai error: {e}")
        await status.edit_text(
            f"<blockquote>❌  ᴇʀʀᴏʀ\n\n<code>{e}</code></blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    # ── parse response ──
    # apifreellm returns {"response": "..."} or {"message": "..."}
    answer = (
        data.get("response")
        or data.get("message")
        or data.get("text")
        or str(data)
    ).strip()

    if not answer:
        await status.edit_text(
            "<blockquote>😔  ᴀɪ ᴋᴀ ᴊᴀᴡᴀʙ ɴᴀʜɪ ᴀʏᴀ. ʙᴀᴀᴅ ᴍᴇ ᴛʀʏ ᴋᴀʀᴏ.</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    full_text = (
        f"<blockquote>🤖  <b>ᴀsᴋ ᴀɪ</b>  |  ❓ <i>{question}</i></blockquote>\n"
        f"<blockquote expandable>{answer}</blockquote>\n"
        f"<blockquote>⏳  ᴀɢʟᴀ ꜱᴀᴡᴀʟ  <b>20ꜱ</b> ʙᴀᴀᴅ ᴘᴜᴄʜʜ ꜱᴀᴋᴛᴇ ʜᴏ.</blockquote>"
    )

    if len(full_text) <= 4096:
        await status.edit_text(full_text, parse_mode=enums.ParseMode.HTML)
    else:
        await status.delete()
        chunks = _split_text(answer, limit=3600)
        header = f"<blockquote>🤖  <b>ᴀsᴋ ᴀɪ</b>  |  ❓ <i>{question}</i></blockquote>\n"
        for i, chunk in enumerate(chunks):
            part = (
                header if i == 0 else
                f"<blockquote>🤖  ᴀsᴋ ᴀɪ  —  ᴘᴀʀᴛ {i + 1}/{len(chunks)}</blockquote>\n"
            )
            part += f"<blockquote expandable>{chunk}</blockquote>"
            if i == len(chunks) - 1:
                part += "\n<blockquote>⏳  ᴀɢʟᴀ ꜱᴀᴡᴀʟ  <b>20ꜱ</b> ʙᴀᴀᴅ ᴘᴜᴄʜʜ ꜱᴀᴋᴛᴇ ʜᴏ.</blockquote>"
            await message.reply_text(part, parse_mode=enums.ParseMode.HTML)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ʜᴇʟᴘᴇʀ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _split_text(text: str, limit: int = 3600) -> list[str]:
    """Long response ko line-breaks pe split karo."""
    chunks, current = [], ""
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
