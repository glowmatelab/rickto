import os
import time
import shutil
import asyncio
import aiohttp
import psutil

from pyrogram import filters, types, enums
from Elevenyts import app, config, db, queue, boot, lang


def fmt_bytes(b):
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} GB"


def status_icon(ok): return "🟢" if ok else "🔴"


async def check_youtube_api() -> tuple[bool, str, float]:
    url = getattr(config, "YOUTUBE_API_URL", "").rstrip("/")
    if not url:
        return False, "Not Set", -1
    try:
        start = time.monotonic()
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{url}/health",
                timeout=aiohttp.ClientTimeout(total=8)
            ) as r:
                latency = round((time.monotonic() - start) * 1000, 1)
                if r.status == 200:
                    return True, f"Online ({latency}ms)", latency
                else:
                    return False, f"HTTP {r.status}", latency
    except asyncio.TimeoutError:
        return False, "Timeout", -1
    except aiohttp.ClientConnectorError:
        return False, "Unreachable", -1
    except Exception:
        return False, "Error", -1


def get_disk_info() -> tuple[float, float, float, float, bool]:
    total, used, free = shutil.disk_usage("/")
    downloads_size = 0
    dl_dir = "downloads"
    if os.path.exists(dl_dir):
        try:
            with os.scandir(dl_dir) as entries:
                for f in entries:
                    try:
                        downloads_size += f.stat().st_size
                    except Exception:
                        pass
        except Exception:
            pass
    disk_critical = (used / total) > 0.88
    return total, used, free, downloads_size, disk_critical


def get_ram_info() -> tuple[float, float, bool]:
    mem = psutil.virtual_memory()
    ram_critical = mem.percent > 85
    return mem.used, mem.total, ram_critical


def get_queue_health() -> tuple[int, int, list]:
    total_queued = 0
    overloaded_chats = []
    active_chat_ids = list(db.active_calls.keys())
    for chat_id in active_chat_ids:
        q = queue.get_queue(chat_id)
        total_queued += len(q)
        if len(q) > 10:
            overloaded_chats.append((chat_id, len(q)))
    return total_queued, len(active_chat_ids), overloaded_chats


def uptime_str() -> str:
    secs = int(time.time() - boot)
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h}h {m}m {s}s"


# ─── Rich Text helpers ────────────────────────────────────────────────────────

def rt_plain(text: str) -> dict:
    return {"@type": "richTextPlain", "text": text}

def rt_bold(text: str) -> dict:
    return {"@type": "richTextBold", "text": rt_plain(text)}

def rt_code(text: str) -> dict:
    return {"@type": "richTextCode", "text": rt_plain(text)}

def rt_concat(*parts) -> dict:
    """Multiple RichText elements joined together."""
    return {"@type": "richTexts", "texts": list(parts)}


# ─── RichBlock helpers ────────────────────────────────────────────────────────

def rb_heading(text: str, level: int = 1) -> dict:
    return {
        "@type": "richBlockSectionHeading",
        "text": rt_plain(text),
        "level": level,
    }

def rb_paragraph(rich_text: dict) -> dict:
    return {"@type": "richBlockParagraph", "text": rich_text}

def rb_divider() -> dict:
    return {"@type": "richBlockDivider"}

def table_cell(content: dict, is_header: bool = False) -> dict:
    return {
        "@type": "richBlockTableCell",
        "text": content,
        "is_header": is_header,
        "colspan": 1,
        "rowspan": 1,
        "align": "left",
        "valign": "middle",
    }

def rb_table(headers: list[str], rows: list[list[dict]]) -> dict:
    """
    headers : list of plain strings  → header row
    rows    : list of rows, each row is a list of RichText dicts
    """
    header_row = [table_cell(rt_bold(h), is_header=True) for h in headers]
    data_rows  = [
        [table_cell(cell) for cell in row]
        for row in rows
    ]
    return {
        "@type": "richBlockTable",
        "caption": {"@type": "richBlockCaption", "text": rt_plain(""), "credit": rt_plain("")},
        "cells": [header_row] + data_rows,
        "is_bordered": True,
        "is_striped": True,
    }

def rb_details(header: str, blocks: list[dict], is_open: bool = False) -> dict:
    """Collapsible / expandable block."""
    return {
        "@type": "richBlockDetails",
        "header": rt_plain(header),
        "blocks": blocks,
        "is_open": is_open,
    }

def rb_block_quote(text: str) -> dict:
    return {
        "@type": "richBlockBlockQuotation",
        "text": rt_plain(text),
        "credit": rt_plain(""),
    }


# ─── Raw Bot API call (Pyrogram doesn't wrap sendRichMessage yet) ─────────────

async def send_rich_message(chat_id: int, blocks: list[dict], reply_to: int | None = None) -> dict:
    token = app.token  # Pyrogram rakhta hai bot token yahan
    payload = {
        "chat_id": chat_id,
        "rich_message": {
            "@type": "inputRichMessage",
            "blocks": blocks,
        },
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to

    url = f"https://api.telegram.org/bot{token}/sendRichMessage"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()


async def edit_rich_message(chat_id: int, message_id: int, blocks: list[dict]) -> dict:
    token = app.token
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "rich_message": {
            "@type": "inputRichMessage",
            "blocks": blocks,
        },
    }
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()


# ─── /health command ──────────────────────────────────────────────────────────

@app.on_message(
    filters.command("health") & filters.user(app.owner)
)
async def health_check(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    # Loading placeholder (plain message, baad mein rich se replace karenge)
    sent = await m.reply_text(
        "📊 <i>Generating diagnostics...</i>",
        parse_mode=enums.ParseMode.HTML
    )

    # ── Data collect ──────────────────────────────────────────────────────────
    api_ok, api_msg, _     = await check_youtube_api()
    total_disk, used_disk, free_disk, dl_size, disk_critical = get_disk_info()
    ram_used, ram_total, ram_critical = get_ram_info()
    cpu                    = psutil.cpu_percent(interval=0.5)
    total_queued, active_chats, overloaded = get_queue_health()

    issues = []
    if not api_ok:    issues.append("YouTube API Down")
    if disk_critical: issues.append("Disk space critical")
    if ram_critical:  issues.append("RAM overload")
    if overloaded:    issues.append(f"{len(overloaded)} chats overloaded")
    if cpu > 85:      issues.append(f"CPU Spike ({cpu}%)")

    overall = "🟢 OPERATIONAL" if not issues else "🔴 ISSUES DETECTED"

    # ── Table rows ────────────────────────────────────────────────────────────
    rows = [
        [rt_plain("YouTube API"),   rt_plain(status_icon(api_ok)),          rt_code(api_msg)],
        [rt_plain("CPU Core"),      rt_plain(status_icon(cpu < 85)),         rt_code(f"{cpu}%")],
        [rt_plain("RAM Memory"),    rt_plain(status_icon(not ram_critical)),  rt_code(f"{round(ram_used/ram_total*100, 1)}%")],
        [rt_plain("Disk Storage"),  rt_plain(status_icon(not disk_critical)), rt_code(f"{round(used_disk/total_disk*100, 1)}%")],
        [rt_plain("Cache Size"),    rt_plain("📦"),                           rt_code(fmt_bytes(dl_size))],
        [rt_plain("Active Rooms"),  rt_plain("🎵"),                           rt_code(f"{active_chats} chats")],
        [rt_plain("Total Queue"),   rt_plain("📜"),                           rt_code(f"{total_queued} songs")],
    ]

    # ── Rich blocks build ─────────────────────────────────────────────────────
    blocks = [
        rb_block_quote(f"🏥 RICKTO SERVER DIAGNOSTICS\nStatus: {overall}\nUptime: {uptime_str()}"),
        rb_divider(),
        rb_heading("🖥️ System Metrics", level=2),
        rb_table(
            headers=["Component", "Status", "Usage / Info"],
            rows=rows,
        ),
    ]

    # Overloaded chats → collapsible block
    if overloaded:
        ol_blocks = [
            rb_paragraph(rt_concat(
                rt_plain(f"• Chat "),
                rt_code(str(cid)),
                rt_plain(f"  →  {cnt} songs"),
            ))
            for cid, cnt in overloaded[:5]
        ]
        blocks.append(rb_details("⚠️ Overloaded Chats (10+)", ol_blocks, is_open=True))

    # Critical alerts
    if issues:
        blocks.append(rb_divider())
        blocks.append(rb_heading("📋 Critical Alerts", level=3))
        for issue in issues:
            blocks.append(rb_paragraph(rt_plain(f"❌ {issue}")))

    # ── Delete loading msg → send rich ────────────────────────────────────────
    try:
        await sent.delete()
    except Exception:
        pass

    await send_rich_message(
        chat_id=m.chat.id,
        blocks=blocks,
    )
