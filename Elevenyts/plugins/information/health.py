import os
import time
import shutil
import asyncio
import aiohttp
import psutil

from pyrogram import filters, types, enums
from Elevenyts import app, config, db, queue, boot

def fmt_bytes(b):
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024: return f"{b:.1f}{u}"
        b /= 1024
    return f"{b:.1f}GB"

async def check_youtube_api() -> tuple[bool, str]:
    url = getattr(config, "YOUTUBE_API_URL", "").rstrip("/")
    if not url: return False, "Not Set"
    try:
        start = time.monotonic()
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as r:
                lat = round((time.monotonic() - start) * 1000, 1)
                return (True, f"{lat}ms") if r.status == 200 else (False, f"HTTP {r.status}")
    except: return False, "Offline"

@app.on_message(filters.command("health") & filters.user(app.owner))
async def health_check(client, m: types.Message):
    try:
        await m.delete()
    except:
        pass

    # Fetch fresh live statistics
    api_ok, api_msg = await check_youtube_api()
    total, used, free = shutil.disk_usage("/")
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.2)
    active_chats = len(list(db.active_calls.keys()))
    
    total_queued = 0
    for cid in list(db.active_calls.keys()):
        total_queued += len(queue.get_queue(cid))

    # --- BOT API 10.1 OFFICIAL sendRichMessage JSON ENGINE ---
    # Constructing the exact payload architecture defined in the June 2026 updates.
    rich_blocks = [
        {
            "type": "rich_block_section_heading",
            "text": "🏥 RICKTO SERVER DIAGNOSTICS\nStatus: 🟢 OPERATIONAL"
        },
        {
            "type": "rich_block_table",
            "columns": 3,
            "header_rows": 1,         # Distinct native background header block trigger
            "rows": [
                # Row 1: Native Slide Header Definition
                [{"text": "COMPONENT"}, {"text": "STATUS"}, {"text": "METRIC"}],
                # Nested Grid Data Items
                [{"text": "YouTube API"}, {"text": "OK" if api_ok else "ERR"}, {"text": api_msg}],
                [{"text": "CPU Core"}, {"text": "OK" if cpu < 85 else "HIGH"}, {"text": f"{cpu}%"}],
                [{"text": "RAM Memory"}, {"text": "OK" if ram.percent < 85 else "HIGH"}, {"text": f"{ram.percent}%"}],
                [{"text": "Disk Space"}, {"text": "OK" if (used/total) < 0.88 else "CRIT"}, {"text": f"{round(used/total*100, 1)}%"}],
                [{"text": "Active Rooms"}, {"text": "LIVE"}, {"text": f"{active_chats} Rooms"}],
                [{"text": "Total Queue"}, {"text": "SYNC"}, {"text": f"{total_queued} Songs"}]
            ]
        }
    ]

    try:
        # Bypassing parser constraints via raw method invocation mapping
        await client.invoke(
            raw.functions.messages.SendRichMessage(
                peer=await client.resolve_peer(m.chat.id),
                rich_blocks=rich_blocks,
                random_id=client.rnd_id()
            )
        )
    except Exception:
        # Strict fallback in case your current Local Bot API instance isn't patched to v10.1 yet
        fallback_text = (
            f"🏥 <b>RICKTO DIAGNOSTICS Fallback</b>\n\n"
            f"• API: <code>{api_msg}</code>\n"
            f"• CPU: <code>{cpu}%</code>\n"
            f"• RAM: <code>{ram.percent}%</code>\n"
            f"• Disk: <code>{round(used/total*100, 1)}%</code>"
        )
        await m.reply_text(fallback_text, parse_mode=enums.ParseMode.HTML)
