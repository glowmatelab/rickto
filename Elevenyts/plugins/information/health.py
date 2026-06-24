import os
import time
import shutil
import asyncio
import aiohttp
import psutil

from pyrogram import filters, types
from Elevenyts import app, config, db, queue, boot, lang


def fmt_bytes(b):
    for u in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} GB"


def status_icon(ok): return "✅" if ok else "❌"


async def check_youtube_api() -> tuple[bool, str, float]:
    """API ka /health endpoint ping karo, latency measure karo."""
    url = getattr(config, "YOUTUBE_API_URL", "").rstrip("/")
    if not url:
        return False, "YOUTUBE_API_URL set nahi hai", -1
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
                    return False, f"HTTP {r.status} ({latency}ms)", latency
    except asyncio.TimeoutError:
        return False, "Timeout (8s se zyada)", -1
    except aiohttp.ClientConnectorError:
        return False, "Connection refused / unreachable", -1
    except Exception as e:
        return False, str(e)[:60], -1


def get_disk_info() -> tuple[float, float, float, bool]:
    """downloads/ folder + total disk usage."""
    total, used, free = shutil.disk_usage("/")
    downloads_size = 0
    dl_dir = "downloads"
    if os.path.exists(dl_dir):
        for f in os.scandir(dl_dir):
            try:
                downloads_size += f.stat().st_size
            except:
                pass
    disk_critical = (used / total) > 0.88  # 88% se zyada = danger
    return total, used, free, downloads_size, disk_critical


def get_ram_info() -> tuple[float, float, bool]:
    mem = psutil.virtual_memory()
    ram_critical = mem.percent > 85
    return mem.used, mem.total, ram_critical


def get_queue_health() -> tuple[int, int, list]:
    """Saare active chats ke queues check karo."""
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


@app.on_message(
    filters.command("health") & filters.user(app.owner)
)
async def health_check(_, m: types.Message):
    try:
        await m.delete()
    except:
        pass

    sent = await m.reply_text("🔍 Running health check...")

    # --- Checks ---
    api_ok, api_msg, api_latency = await check_youtube_api()
    total_disk, used_disk, free_disk, dl_size, disk_critical = get_disk_info()
    ram_used, ram_total, ram_critical = get_ram_info()
    cpu = psutil.cpu_percent(interval=0.5)
    total_queued, active_chats, overloaded = get_queue_health()

    # Overall status
    issues = []
    if not api_ok:
        issues.append("YouTube API down")
    if disk_critical:
        issues.append("Disk almost full")
    if ram_critical:
        issues.append("RAM overloaded")
    if overloaded:
        issues.append(f"{len(overloaded)} chat(s) queue overloaded (10+)")
    if cpu > 85:
        issues.append(f"CPU high ({cpu}%)")

    overall = "🟢 All systems OK" if not issues else "🔴 Issues detected"

    # --- Report build ---
    report = f"""<blockquote><b>🏥 RICKTO HEALTH REPORT</b></blockquote>

<b>Status:</b> {overall}

━━━━━━━━━━━━━━━━━━━━
<b>🌐 YouTube Download API</b>
  {status_icon(api_ok)} <b>Status:</b> {api_msg}
  <b>URL:</b> <code>{getattr(config, 'YOUTUBE_API_URL', 'N/A')}</code>

━━━━━━━━━━━━━━━━━━━━
<b>💾 Disk Usage</b>
  {status_icon(not disk_critical)} <b>Total:</b> {fmt_bytes(total_disk)}
  <b>Used:</b> {fmt_bytes(used_disk)} ({round(used_disk/total_disk*100, 1)}%)
  <b>Free:</b> {fmt_bytes(free_disk)}
  <b>Downloads folder:</b> {fmt_bytes(dl_size)}
  {'⚠️ <b>Disk critical! /restart karo ya downloads clean karo</b>' if disk_critical else ''}

━━━━━━━━━━━━━━━━━━━━
<b>🧠 RAM</b>
  {status_icon(not ram_critical)} {fmt_bytes(ram_used)} / {fmt_bytes(ram_total)} ({round(ram_used/ram_total*100,1)}%)
  {'⚠️ <b>RAM critical! Bot slow ho sakta hai</b>' if ram_critical else ''}

━━━━━━━━━━━━━━━━━━━━
<b>⚙️ CPU</b>
  {status_icon(cpu < 85)} {cpu}%

━━━━━━━━━━━━━━━━━━━━
<b>🎵 Queue Status</b>
  <b>Active voice chats:</b> {active_chats}
  <b>Total songs queued:</b> {total_queued}"""

    if overloaded:
        report += "\n  ⚠️ <b>Overloaded chats (10+ songs):</b>"
        for cid, cnt in overloaded[:5]:
            report += f"\n    • <code>{cid}</code> → {cnt} songs"

    report += f"""

━━━━━━━━━━━━━━━━━━━━
<b>🕐 Uptime:</b> {uptime_str()}"""

    if issues:
        report += "\n\n━━━━━━━━━━━━━━━━━━━━\n<b>⚠️ Issues Summary:</b>"
        for i in issues:
            report += f"\n  • {i}"

    report += "\n</blockquote>"

    await sent.edit_text(report, parse_mode="html")
