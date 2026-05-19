"""
Sticker Mode Plugin
───────────────────
Commands:
  /stickermode on   – enable sticker after every play (per group)
  /stickermode off  – disable

How it works:
  • State lives in a plain Python set (in-memory).
  • Zero DB calls, zero extra RAM beyond a few integers.
  • On bot restart the setting resets to OFF — totally fine for a
    lightweight Render deployment.

Sticker list:
  Add as many file_id strings to STICKERS as you like.
  random.choice() picks one per play — still O(1), no allocation.
"""

import random
from pyrogram import filters
from pyrogram.types import Message
from Elevenyts import app
from Elevenyts.helpers._admins import admins_only   # reuse existing admin guard

# ── sticker pool ────────────────────────────────────────────────────────────
# Add more file_ids here whenever you want a bigger pool.
STICKERS: list[str] = [
    "CAACAgUAAxkBAAIFa2oMVwZ8gLH2WgABrHd6MWbzRujBbwACqR0AAr06WVSEzFFuDRcP-TsE",
    # "CAACAgU...another_sticker_id...",
]

# ── in-memory state  {chat_id: bool} ────────────────────────────────────────
# This dict is the ONLY runtime cost — one integer key per group that uses /stickermode.
_sticker_mode: dict[int, bool] = {}


# ── public helpers (imported by calls.py) ───────────────────────────────────

def is_sticker_mode(chat_id: int) -> bool:
    """Return True if sticker mode is ON for this chat."""
    return _sticker_mode.get(chat_id, False)


def get_random_sticker() -> str:
    """Return a random sticker file_id from the pool."""
    return random.choice(STICKERS)


# ── command handler ──────────────────────────────────────────────────────────

@app.on_message(
    filters.command(["stickermode", "stickmode"])
    & filters.group
)
@admins_only
async def stickermode_cmd(_, message: Message):
    args = message.command
    chat_id = message.chat.id

    if len(args) < 2 or args[1].lower() not in ("on", "off"):
        current = "✅ ON" if is_sticker_mode(chat_id) else "❌ OFF"
        await message.reply_text(
            f"<blockquote>"
            f"🎭 <b>Sticker Mode</b>\n\n"
            f"Current status: <b>{current}</b>\n\n"
            f"Usage:\n"
            f"  <code>/stickermode on</code>  – play ke baad sticker bhejega\n"
            f"  <code>/stickermode off</code> – band karo"
            f"</blockquote>"
        )
        return

    enable = args[1].lower() == "on"
    _sticker_mode[chat_id] = enable

    status_text = "✅ <b>ON</b> kar diya!" if enable else "❌ <b>OFF</b> kar diya!"
    await message.reply_text(
        f"<blockquote>"
        f"🎭 <b>Sticker Mode {status_text}</b>\n\n"
        + (
            "Ab har play ke baad ek random sticker aayega! 🎉"
            if enable else
            "Sticker band ho gaya."
        )
        + "</blockquote>"
    )
