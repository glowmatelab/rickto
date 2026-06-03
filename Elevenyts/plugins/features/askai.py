# Elevenyts/plugins/features/askai.py
# AI Ask — apifreellm.com (20 sec cooldown per user)

import time
import aiohttp
import logging
import asyncio
from pyrogram import filters, enums
from pyrogram.types import Message
from Elevenyts import app
from Elevenyts import config

logger = logging.getLogger(__name__)

ASKAI_API   = "https://apifreellm.com/api/v1/chat"
COOLDOWN    = 20  # seconds
ASKAI_TOKEN = config.ASKAI_API_KEY

# ── in-memory cooldown store ──
_cooldowns: dict[int, float] = {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ʜᴇʟᴘᴇʀs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get_name(user) -> str:
    """User ka first name + last name (if any) return karo."""
    if not user:
        return "Unknown"
    name = user.first_name or ""
    if user.last_name:
        name += f" {user.last_name}"
    return name.strip() or "Unknown"


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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /askai ᴄᴏᴍᴍᴀɴᴅ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("askai") & (filters.group | filters.private))
async def askai_cmd(_, message: Message):
    user_id   = message.from_user.id
    user_name = _get_name(message.from_user)
    question  = " ".join(message.command[1:]).strip()

    # ── No question given ──
    if not question:
        await message.reply_text(
            "╔═══════════════════╗\n"
            "║   🤖  **ᴀsᴋ ᴀɪ**   ║\n"
            "╚═══════════════════╝\n\n"
            "⚠️ Kuch toh pooch bhai!\n\n"
            "**Usage:**\n"
            " `/askai What is AI?`\n"
            " `/askai Python kya hota hai?`",
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return

    # ── Cooldown check ──
    now      = time.time()
    last     = _cooldowns.get(user_id, 0)
    remaining = COOLDOWN - (now - last)

    if remaining > 0:
        secs = int(remaining) + 1
        await message.reply_text(
            f"⏳ **Zra ruk {user_name}!**\n\n"
            f"**{secs}s** baad pooch sakte ho.\n"
            f"🔁 Har sawal ke baad **20s** cooldown hai.",
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return

    # ── Mark cooldown ──
    _cooldowns[user_id] = now

    # ── Send "Thinking..." with username and question ──
    thinking_text = (
        f"**✦ Ask AI**\n"
        f"**›** {user_name}: {question}\n\n"
        f"**⊷** `Thinking...`"
    )
    status = await message.reply_text(
        thinking_text,
        parse_mode=enums.ParseMode.MARKDOWN,
    )

    # ── Animated dots while waiting ──
    dots_task = asyncio.create_task(
        _animate_thinking(status, user_name, question)
    )

    # ── API call ──
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
                    raw_err = await resp.text()
                    logger.error(f"askai API error {resp.status}: {raw_err}")
                    dots_task.cancel()
                    await status.edit_text(
                        f"❌ **API Error** — `{resp.status}`",
                        parse_mode=enums.ParseMode.MARKDOWN,
                    )
                    return

                data = await resp.json()

    except aiohttp.ClientConnectorError as e:
        logger.error(f"askai connection error: {e}")
        dots_task.cancel()
        await status.edit_text(
            "❌ **API unreachable.** Baad mein try karo.",
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return
    except asyncio.TimeoutError:
        logger.error("askai API timeout")
        dots_task.cancel()
        await status.edit_text(
            "❌ **Request timeout.** API ne 30s mein jawab nahi diya.",
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return
    except Exception as e:
        logger.error(f"askai unknown error: {e}")
        dots_task.cancel()
        await status.edit_text(
            f"❌ **Error**\n\n`{e}`",
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return

    # ── Stop animation ──
    dots_task.cancel()

    # ── Parse answer ──
    answer = (
        data.get("response")
        or data.get("message")
        or data.get("text")
        or str(data)
    ).strip()

    # ── Final formatted message — blockquote with expandable answer ──
    # Expandable blockquote: lines prefixed with "**>**", last line "**>||**"
    answer_lines = answer.splitlines()
    if answer_lines:
        quoted = "\n".join(f"**>** {line}" if line.strip() else "**>**" for line in answer_lines[:-1])
        quoted += ("\n" if answer_lines[:-1] else "") + f"**>** {answer_lines[-1]}||"
    else:
        quoted = f"**>** {answer}||"

    full_text = (
        f"**✦ Ask AI**\n"
        f"**›** {user_name}: {question}\n\n"
        f"{quoted}\n\n"
        f"_⏳ Next question in 20s_"
    )

    if len(full_text) <= 4096:
        await status.edit_text(full_text, parse_mode=enums.ParseMode.MARKDOWN)
    else:
        await status.delete()
        chunks = _split_text(answer, limit=3200)
        for i, chunk in enumerate(chunks):
            chunk_lines = chunk.splitlines()
            if chunk_lines:
                q = "\n".join(f"**>** {l}" if l.strip() else "**>**" for l in chunk_lines[:-1])
                q += ("\n" if chunk_lines[:-1] else "") + f"**>** {chunk_lines[-1]}||"
            else:
                q = f"**>** {chunk}||"

            if i == 0:
                part = f"**✦ Ask AI**\n**›** {user_name}: {question}\n\n{q}"
            else:
                part = f"**✦ Ask AI** — Part {i+1}/{len(chunks)}\n\n{q}"

            if i == len(chunks) - 1:
                part += "\n\n_⏳ Next question in 20s_"

            await message.reply_text(part, parse_mode=enums.ParseMode.MARKDOWN)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ᴀɴɪᴍᴀᴛɪᴏɴ ʜᴇʟᴘᴇʀ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _animate_thinking(status, user_name: str, question: str):
    """Thinking message mein animated dots update karo jab tak API respond kare."""
    frames = ["Thinking ⏳", "Thinking. ⏳", "Thinking.. ⏳", "Thinking... ⏳"]
    i = 0
    try:
        while True:
            await asyncio.sleep(2)
            frame = frames[i % len(frames)]
            i += 1
            try:
                await status.edit_text(
                    f"**✦ Ask AI**\n"
                    f"**›** {user_name}: {question}\n\n"
                    f"**⊷** `{frame}`",
                    parse_mode=enums.ParseMode.MARKDOWN,
                )
            except Exception:
                break  # Message delete ho gaya ya flood wait — stop karo
    except asyncio.CancelledError:
        pass  # Normal cancellation when API responds
