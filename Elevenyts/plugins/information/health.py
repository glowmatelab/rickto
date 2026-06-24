import os
import time
import shutil
import asyncio
import aiohttp
import psutil
from telegramify_markdown import richify

from pyrogram import filters, types
from Elevenyts import app, config, db, queue, boot


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
            async with s.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=8)) as r:
                latency = round((time.monotonic() - start) * 1000, 1)
                return (True, f"Online ({latency}ms)", latency) if r.status == 200 else (False, f"HTTP {r.status}", latency)
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
    return total, used, free, downloads_size, (used / total) > 0.88


def get_ram_info() -> tuple[float, float, bool]:
    mem = psutil.virtual_memory()
    return mem.used, mem.total, mem.percent > 85


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


async def send_rich(chat_id: int, md: str) -> dict:
    token = config.BOT_TOKEN
    rich_message = richify(md)
    async with aiohttp.ClientSession() as s:
        r = await s.post(
            f"https://api.telegram.org/bot{token}/sendRichMessage",
            json={"chat_id": chat_id, "rich_message": rich_message.to_dict()}
        )
        return await r.json()


@app.on_message(filters.command("health") & filters.user(app.owner))
async def health_check(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    sent = await m.reply_text("📊 <i>Generating diagnostics...</i>")

    api_ok, api_msg, _                      = await check_youtube_api()
    total_disk, used_disk, _, dl_size, disk_critical = get_disk_info()
    ram_used, ram_total, ram_critical        = get_ram_info()
    cpu                                      = psutil.cpu_percent(interval=0.5)
    total_queued, active_chats, overloaded   = get_queue_health()

    issues = []
    if not api_ok:    issues.append("YouTube API Down")
    if disk_critical: issues.append("Disk space critical")
    if ram_critical:  issues.append("RAM overload")
    if overloaded:    issues.append(f"{len(overloaded)} chats overloaded")
    if cpu > 85:      issues.append(f"CPU Spike ({cpu}%)")

    overall = "🟢 OPERATIONAL" if not issues else "🔴 ISSUES DETECTED"

    md = f"""# 🏥 RICKTO DIAGNOSTICS
**Status:** {overall}
**Uptime:** `{uptime_str()}`

## 🖥️ System Metrics

| Component | Status | Info |
| --- | --- | --- |
| YouTube API | {status_icon(api_ok)} | `{api_msg}` |
| CPU | {status_icon(cpu < 85)} | `{cpu}%` |
| RAM | {status_icon(not ram_critical)} | `{round(ram_used / ram_total * 100, 1)}%` |
| Disk | {status_icon(not disk_critical)} | `{round(used_disk / total_disk * 100, 1)}%` |
| Cache | 📦 | `{fmt_bytes(dl_size)}` |
| Active Rooms | 🎵 | `{active_chats} chats` |
| Queue | 📜 | `{total_queued} songs` |
"""

    if overloaded:
        md += "\n## ⚠️ Overloaded Chats\n"
        for cid, cnt in overloaded[:5]:
            md += f"- Chat `{cid}` → **{cnt} songs**\n"

    if issues:
        md += "\n## 📋 Critical Alerts\n"
        for issue in issues:
            md += f"- ❌ {issue}\n"

    try:
        await sent.delete()
    except Exception:
        pass

    result = await send_rich(chat_id=m.chat.id, md=md)

    if not result.get("ok"):
        await m.reply_text(
            f"<blockquote><b>🏥 RICKTO DIAGNOSTICS</b>\n"
            f"Status: <b>{overall}</b>\nUptime: <code>{uptime_str()}</code></blockquote>\n\n"
            + ("\n".join(f"❌ <i>{i}</i>" for i in issues) if issues else "✅ All systems normal")
        )
