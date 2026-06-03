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

# Set up logging to show everything in terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ASKAI_API   = "https://apifreellm.com/api/v1/chat"   
COOLDOWN    = 20  # seconds
ASKAI_TOKEN = config.ASKAI_API_KEY

print(f"==========================================")
print(f"🤖 ASKAI PLUGIN LOADING...")
print(f"🔑 Loaded Token: {ASKAI_TOKEN[:5] if ASKAI_TOKEN else 'NONE'}... (Length: {len(str(ASKAI_TOKEN)) if ASKAI_TOKEN else 0})")
print(f"==========================================")

# ── in-memory cooldown store: {user_id: last_used_timestamp} ──
_cooldowns: dict[int, float] = {}


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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /askai ᴄᴏᴍᴍᴀɴᴅ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("askai") & (filters.group | filters.private))
async def askai_cmd(_, message: Message):
    user_id = message.from_user.id
    question = " ".join(message.command[1:]).strip()
    
    # 📝 DEBUG 1: Command trigger check
    print(f"\n[DEBUG] 🚀 /askai command triggered by User ID: {user_id}")
    print(f"[DEBUG] 📝 Question received: '{question}'")

    if not question:
        print("[DEBUG] ⚠️ Question khali hai, usage message bhej raha hu.")
        await message.reply_text(
            "🤖 **ᴀsᴋ ᴀɪ**\n\n"
            "⚠️ ꜱᴏᴍᴇᴛʜɪɴɢ ᴛᴏ ᴀsᴋ ᴍᴜᴊʜᴇ ʙᴛᴀ?\n\n"
            "**ʜᴏᴡ ᴛᴏ ᴜsᴇ :**\n"
            " `/askai What is AI?`\n"
            " `/askai Python kya hota hai?`",
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return

    # ── cooldown check ──
    now = time.time()
    last_used = _cooldowns.get(user_id, 0)
    remaining = COOLDOWN - (now - last_used)

    if remaining > 0:
        secs = int(remaining) + 1
        print(f"[DEBUG] ⏳ User {user_id} cooldown par hai. {secs}s bache hain.")
        await message.reply_text(
            f"⏳ ʏᴀᴀʀ ᴢʀᴀ ʀᴜᴋ! **{secs}s** ʙᴀᴀᴅ ᴘᴜᴄʜʜ.\n\n"
            "🔁 ʜᴀʀ ꜱᴀᴡᴀʟ ᴋᴇ ʙᴀᴀᴅ **20 ꜱᴇᴄ** ᴋᴀ ᴄᴏᴏʟᴅᴏᴡɴ ʜᴀɪ.",
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return

    # ── mark cooldown ──
    _cooldowns[user_id] = now

    print("[DEBUG] 🤖 Status message (Thinking...) send ho raha hai.")
    status = await message.reply_text(
        "🤖 **ᴀɪ ꜱᴏᴄʜ ʀᴀʜᴀ ʜᴀɪ...**\n\n"
        f"❓ `{question}`",
        parse_mode=enums.ParseMode.MARKDOWN,
    )

    # 📝 DEBUG 2: API Request bhejne se pehle data check
    print(f"[DEBUG] 🌐 API call start ho rahi hai...")
    print(f"[DEBUG] 🔗 URL: {ASKAI_API}")
    print(f"[DEBUG] 🎫 Token used: Bearer {ASKAI_TOKEN[:5] if ASKAI_TOKEN else 'NONE'}...")

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

                # 📝 DEBUG 3: Status code check
                print(f"[DEBUG] 📥 API Response Status Code: {resp.status}")

                if resp.status != 200:
                    raw_err = await resp.text()
                    print(f"[DEBUG] ❌ API fail hui. Error Raw Response: {raw_err}")
                    await status.edit_text(
                        f"❌ ᴀᴘɪ ᴇʀʀᴏʀ — `{resp.status}`",
                        parse_mode=enums.ParseMode.MARKDOWN,
                    )
                    return

                data = await resp.json()
                # 📝 DEBUG 4: API se kya JSON aaya pura print karein
                print(f"[DEBUG] ✅ API JSON Data Received: {data}")

    except aiohttp.ClientConnectorError as e:
        print(f"[DEBUG] ❌ Connection Error: {e}")
        await status.edit_text("❌ ᴀᴘɪ ᴜɴʀᴇᴀᴄʜᴀʙʟᴇ. ʙᴀᴀᴅ ᴍᴇ ᴛʀʏ ᴋᴀʀᴏ.", parse_mode=enums.ParseMode.MARKDOWN)
        return
    except asyncio.TimeoutError:
        print("[DEBUG] ❌ API Timeout ho gayi (30 seconds limit)!")
        await status.edit_text("❌ ʀᴇqᴜᴇꜱᴛ ᴛɪᴍᴇᴏᴜᴛ. ʙᴀᴀᴅ ᴍᴇ ᴛʀʏ ᴋᴀʀᴏ.", parse_mode=enums.ParseMode.MARKDOWN)
        return
    except Exception as e:
        print(f"[DEBUG] ❌ Unknown Exception raised: {e}")
        logger.error(f"askai error: {e}")
        await status.edit_text(
            f"❌ ᴇʀʀᴏʀ\n\n`{e}`",
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return

    # ── parse response ──
    answer = (
        data.get("response")
        or data.get("message")
        or data.get("text")
        or str(data)
    ).strip()

    print(f"[DEBUG] 🧠 Parsed Answer String: {answer[:100]}...")

    if not answer or answer == str(data):
        print(f"[DEBUG] ⚠️ Warning: Answer key direct nahi mili, fallback text ya empty mila.")

    # Format output text using Markdown for safe and beautiful UI
    full_text = (
        f"🤖 **ᴀsᴋ ᴀɪ** | ❓ _{question}_\n\n"
        f"{answer}\n\n"
        f"⏳ ᴀɢʟᴀ ꜱᴀᴡᴀʟ **20ꜱ** ʙᴀᴀᴅ ᴘᴜᴄʜʜ ꜱᴀᴋᴛᴇ ʜᴏ."
    )

    if len(full_text) <= 4096:
        print("[DEBUG] 📤 Message short hai (under 4096). Editing status message...")
        await status.edit_text(full_text, parse_mode=enums.ParseMode.MARKDOWN)
    else:
        print(f"[DEBUG] ✂️ Message bada hai ({len(full_text)} chars). Splitting into chunks...")
        await status.delete()
        chunks = _split_text(answer, limit=3600)
        header = f"🤖 **ᴀsᴋ ᴀɪ** | ❓ _{question}_\n\n"
        for i, chunk in enumerate(chunks):
            part = (
                header if i == 0 else
                f"🤖 ᴀsᴋ ᴀɪ — ᴘᴀʀᴛ {i + 1}/{len(chunks)}\n\n"
            )
            part += chunk
            if i == len(chunks) - 1:
                part += "\n\n⏳ ᴀɢʟᴀ ꜱᴀᴡᴀʟ **20ꜱ** ʙᴀᴀᴅ ᴘᴜᴄʜʜ ꜱᴀᴋᴛᴇ ʜᴏ."
            await message.reply_text(part, parse_mode=enums.ParseMode.MARKDOWN)
    print("[DEBUG] ✅ Process Complete for this request.\n")
