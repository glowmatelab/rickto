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
            return f"{b:.1f}{u}"
        b /= 1024
    return f"{b:.1f}GB"


def status_str(ok): return "OK" if ok else "ERR"


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
                    return True, f"{latency}ms", latency
                else:
                    return False, f"H-{r.status}", latency
    except asyncio.TimeoutError:
        return False, "Timeout", -1
    except aiohttp.ClientConnectorError:
        return False, "Unreach", -1
    except Exception as e:
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
                    except:
                        pass
        except:
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


@app.on_message(
    filters.command("health") & filters.user(app.owner)
)
async def health_check(_, m: types.Message):
    try:
        await m.delete()
    except:
        pass

    sent = await m.reply_text("📊 <i>Rendering rigid text matrix...</i>", parse_mode=enums.ParseMode.HTML)

    # --- Diagnostics Data ---
    api_ok, api_msg, api_latency = await check_youtube_api()
    total_disk, used_disk, free_disk, dl_size, disk_critical = get_disk_info()
    ram_used, ram_total, ram_critical = get_ram_info()
    cpu = psutil.cpu_percent(interval=0.5)
    total_queued, active_chats, overloaded = get_queue_health()

    issues = []
    if not api_ok: issues.append("YouTube API Down")
    if disk_critical: issues.append("Disk space critical")
    if ram_critical: issues.append("RAM overload")
    if overloaded: issues.append(f"{len(overloaded)} chats overloaded")
    if cpu > 85: issues.append(f"CPU Spike ({cpu}%)")

    overall_status = "🟢 OPERATIONAL" if not issues else "🔴 ALERT ISSUES"

    # --- Strict Document Layout (Responsive Grid Builder) ---
    # Har column ki length fixed kari hai taaki grid mobile screen par break na ho.
    comp_w, stat_w, info_w = 12, 6, 12
    
    def r_row(c, s, i):
        return f"│{c:<{comp_w}}│{s:^{stat_w}}│{i:<{info_w}}│\n"

    grid_table = "┌" + "─"*comp_w + "┬" + "─"*stat_w + "┬" + "─"*info_w + "┐\n"
    grid_table += r_row("Component", "Status", "Usage/Info")
    grid_table += "├" + "─"*comp_w + "┼" + "─"*stat_w + "┼" + "─"*info_w + "┤\n"
    
    grid_table += r_row("YouTube API", status_str(api_ok), api_msg)
    grid_table += r_row("CPU Core", status_str(cpu < 85), f"{cpu}%")
    grid_table += r_row("RAM Memory", status_str(not ram_critical), f"{round(ram_used/ram_total*100, 1)}%")
    grid_table += r_row("Disk Storage", status_str(not disk_critical), f"{round(used_disk/total_disk*100, 1)}%")
    grid_table += r_row("Cache Size", "OK", fmt_bytes(dl_size))
    grid_table += r_row("Active Rooms", "OK", f"{active_chats} Chats")
    grid_table += r_row("Total Queue", "OK", f"{total_queued} Songs")
    grid_table += "└" + "─"*comp_w + "┴" + "─"*stat_w + "┴" + "─"*info_w + "┘"

    # --- Report Build ---
    report = f"""<blockquote><b>🏥 RICKTO SERVER DIAGNOSTICS</b>
Status: <b>{overall_status}</b>
Uptime: <code>{uptime_str()}</code></blockquote>

<b>🖥️ SYSTEM MATRIX DATA:</b>
<pre>{grid_table}</pre>

<b>🌐 Hidden Endpoint:</b> <spoiler>{getattr(config, 'YOUTUBE_API_URL', 'Not Set')}</spoiler>"""

    if overloaded:
        report += "\n\n<blockquote expandable><b>⚠️ OVERLOADED CHATS (10+)</b>"
        for cid, cnt in overloaded[:5]:
            report += f"\n• <code>{cid}</code> ➜ <b>{cnt} songs</b>"
        report += "</blockquote>"

    if issues:
        report += "\n\n📋 <b>CRITICAL ALERTS:</b>"
        for issue in issues:
            report += f"\n❌ <i>{issue}</i>"

    await sent.edit_text(report, parse_mode=enums.ParseMode.HTML)
