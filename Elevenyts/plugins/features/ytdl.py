# Elevenyts/plugins/features/ytdl.py
# YouTube + Instagram Downloader

import os
import re
import asyncio
import logging
from pyrogram import filters, enums
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from Elevenyts import app, yt

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ᴜᴛɪʟɪᴛɪᴇs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YT_REGEX = re.compile(
    r"(https?://)?(www\.|m\.|music\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
)

IG_REGEX = re.compile(
    r"(https?://)?(www\.)?instagram\.com/(reel|p|tv)/([A-Za-z0-9_-]+)/?"
)


def detect_platform(url: str):
    if YT_REGEX.search(url):
        return "youtube"
    if IG_REGEX.search(url):
        return "instagram"
    return None


def extract_link(message: Message):
    targets = [message]
    if message.reply_to_message:
        targets.append(message.reply_to_message)

    for msg in targets:
        text = msg.text or msg.caption or ""
        entities = msg.entities or msg.caption_entities or []

        for entity in entities:
            if entity.type == enums.MessageEntityType.URL:
                link = text[entity.offset: entity.offset + entity.length]
                if detect_platform(link):
                    return link.split("&si")[0].split("?si")[0]
            elif entity.type == enums.MessageEntityType.TEXT_LINK:
                if detect_platform(entity.url):
                    return entity.url

        for word in text.split():
            if detect_platform(word):
                return word.split("&si")[0].split("?si")[0]

    return None


def extract_video_id(url: str):
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


def extract_ig_shortcode(url: str):
    match = IG_REGEX.search(url)
    return match.group(4) if match else None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ʏᴏᴜᴛᴜʙᴇ ᴅᴏᴡɴʟᴏᴀᴅ ᴠɪᴀ ʏᴛ-ᴅʟᴘ  (ʀᴇꜱᴏʟᴜᴛɪᴏɴ)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Resolution map: key → (format_selector, label)
YT_RESOLUTIONS = {
    "360": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]",
    "720": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
    "1080": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]",
}


async def download_youtube_video(video_id: str, resolution: str) -> str | None:
    os.makedirs("downloads", exist_ok=True)

    out_path = f"downloads/yt_{video_id}_{resolution}p.mp4"
    url = f"https://www.youtube.com/watch?v={video_id}"

    if os.path.exists(out_path):
        return out_path

    fmt = YT_RESOLUTIONS.get(resolution, YT_RESOLUTIONS["720"])

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", fmt,
        "--merge-output-format", "mp4",
        "-o", out_path,
        url,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode == 0 and os.path.exists(out_path):
            return out_path
        else:
            logger.error(f"yt-dlp video error: {stderr.decode()[-300:]}")
            return None

    except asyncio.TimeoutError:
        logger.error("YouTube video download timeout")
        return None
    except Exception as e:
        logger.error(f"YouTube video download error: {e}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ɪɴsᴛᴀɢʀᴀᴍ ᴅᴏᴡɴʟᴏᴀᴅ ᴠɪᴀ ʏᴛ-ᴅʟᴘ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def download_instagram(url: str, audio_only: bool = False) -> str | None:
    os.makedirs("downloads", exist_ok=True)

    shortcode = extract_ig_shortcode(url)
    if not shortcode:
        return None

    ext = "mp3" if audio_only else "mp4"
    out_path = f"downloads/ig_{shortcode}.{ext}"

    if os.path.exists(out_path):
        return out_path

    if audio_only:
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "192K",                         # ✅ FIX: VBR "0" ki jagah fixed 192K
            "--postprocessor-args", "ffmpeg:-ar 44100 -ac 2",  # ✅ FIX: sample rate + stereo force
            "-o", out_path,
            url,
        ]
    else:
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", out_path,
            url,
        ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode == 0 and os.path.exists(out_path):
            return out_path
        else:
            logger.error(f"yt-dlp ig error: {stderr.decode()[-300:]}")
            return None

    except asyncio.TimeoutError:
        logger.error("Instagram download timeout")
        return None
    except Exception as e:
        logger.error(f"Instagram download error: {e}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /download ᴄᴏᴍᴍᴀɴᴅ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("download") & (filters.group | filters.private))
async def download_cmd(_, message: Message):
    link = extract_link(message)

    if not link:
        await message.reply_text(
            "<blockquote>"
            "⚠️  ʟɪɴᴋ ɴᴏᴛ ꜰᴏᴜɴᴅ\n\n"
            "ꜱᴜᴘᴘᴏʀᴛᴇᴅ :\n"
            "  ▸  ʏᴏᴜᴛᴜʙᴇ  —  ᴠɪᴅᴇᴏ / ꜱʜᴏʀᴛꜱ\n"
            "  ▸  ɪɴꜱᴛᴀɢʀᴀᴍ  —  ʀᴇᴇʟ / ᴘᴏꜱᴛ\n\n"
            "ʜᴏᴡ ᴛᴏ ᴜꜱᴇ :\n"
            "  ➊  ꜱᴇɴᴅ ᴀ ʟɪɴᴋ\n"
            "  ➋  ʀᴇᴘʟʏ ᴛᴏ ɪᴛ ᴡɪᴛʜ  /download"
            "</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    platform = detect_platform(link)

    # ── YouTube ──
    if platform == "youtube":
        video_id = extract_video_id(link)
        if not video_id:
            await message.reply_text(
                "<blockquote>❌  ᴠᴀʟɪᴅ ᴠɪᴅᴇᴏ ɪᴅ ɴᴏᴛ ꜰᴏᴜɴᴅ.</blockquote>",
                parse_mode=enums.ParseMode.HTML,
            )
            return

        # Resolution buttons + Audio
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📱  360p", callback_data=f"ytdl_360_{video_id}"),
                InlineKeyboardButton("🖥  720p", callback_data=f"ytdl_720_{video_id}"),
                InlineKeyboardButton("🎞  1080p", callback_data=f"ytdl_1080_{video_id}"),
            ],
            [
                InlineKeyboardButton("𝄞  ᴀᴜᴅɪᴏ ᴏɴʟʏ", callback_data=f"ytdl_audio_{video_id}"),
            ],
            [InlineKeyboardButton("✕  ᴄᴀɴᴄᴇʟ", callback_data="ytdl_cancel")],
        ])

        await message.reply_text(
            "<blockquote>"
            "📥  sᴇʟᴇᴄᴛ ꜰᴏʀᴍᴀᴛ  —  ʏᴏᴜᴛᴜʙᴇ\n\n"
            f"🔗  <code>{link}</code>"
            "</blockquote>",
            reply_markup=markup,
            parse_mode=enums.ParseMode.HTML,
        )

    # ── Instagram ──
    elif platform == "instagram":
        shortcode = extract_ig_shortcode(link)
        if not shortcode:
            await message.reply_text(
                "<blockquote>❌  ɪɴsᴛᴀɢʀᴀᴍ ʟɪɴᴋ ɪɴᴠᴀʟɪᴅ.</blockquote>",
                parse_mode=enums.ParseMode.HTML,
            )
            return

        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("𝄞  ᴀᴜᴅɪᴏ", callback_data=f"igdl_audio_{shortcode}"),
                InlineKeyboardButton("⬡  ᴠɪᴅᴇᴏ", callback_data=f"igdl_video_{shortcode}"),
            ],
            [InlineKeyboardButton("✕  ᴄᴀɴᴄᴇʟ", callback_data="ytdl_cancel")],
        ])

        await message.reply_text(
            "<blockquote>"
            "📥  sᴇʟᴇᴄᴛ ꜰᴏʀᴍᴀᴛ  —  ɪɴsᴛᴀɢʀᴀᴍ\n\n"
            f"🔗  <code>{link}</code>"
            "</blockquote>",
            reply_markup=markup,
            parse_mode=enums.ParseMode.HTML,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ᴄᴀʟʟʙᴀᴄᴋ  —  ʏᴏᴜᴛᴜʙᴇ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_callback_query(filters.regex(r"^ytdl_(audio|360|720|1080|cancel)_?(.*)$"))
async def ytdl_callback(_, query: CallbackQuery):
    data = query.data

    if data == "ytdl_cancel":
        await query.message.delete()
        await query.answer("ᴄᴀɴᴄᴇʟʟᴇᴅ")
        return

    parts = data.split("_", 2)
    if len(parts) < 3:
        await query.answer("ɪɴᴠᴀʟɪᴅ ʀᴇqᴜᴇꜱᴛ", show_alert=True)
        return

    mode = parts[1]       # "audio" | "360" | "720" | "1080"
    video_id = parts[2]
    is_audio = mode == "audio"

    await query.answer("ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ...")

    label = "ᴀᴜᴅɪᴏ" if is_audio else f"{mode}ᴘ ᴠɪᴅᴇᴏ"

    status = await query.message.edit_text(
        "<blockquote>"
        f"⏳  ʏᴏᴜᴛᴜʙᴇ  {label}  ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ...\n\n"
        f"🆔  <code>{video_id}</code>"
        "</blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )

    file_path = None
    try:
        if is_audio:
            # Purana yt helper use karo audio ke liye
            file_path = await yt.download(video_id=video_id, is_live=False, video=False)
        else:
            # Naya resolution-based download
            file_path = await download_youtube_video(video_id, resolution=mode)

        if not file_path or not os.path.exists(file_path):
            await status.edit_text(
                "<blockquote>"
                "❌  ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ\n\n"
                "ᴠɪᴅᴇᴏ ᴍᴀʏ ʙᴇ ʀᴇꜱᴛʀɪᴄᴛᴇᴅ ᴏʀ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ."
                "</blockquote>",
                parse_mode=enums.ParseMode.HTML,
            )
            return

        await _send_file(query, status, file_path, not is_audio, "ʏᴏᴜᴛᴜʙᴇ", label)

    except Exception as e:
        logger.error(f"ytdl error: {e}")
        try:
            await status.edit_text(
                f"<blockquote>❌  ᴇʀʀᴏʀ\n\n<code>{e}</code></blockquote>",
                parse_mode=enums.ParseMode.HTML,
            )
        except Exception:
            pass
    finally:
        _cleanup(file_path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ᴄᴀʟʟʙᴀᴄᴋ  —  ɪɴsᴛᴀɢʀᴀᴍ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_callback_query(filters.regex(r"^igdl_(audio|video)_(.+)$"))
async def igdl_callback(_, query: CallbackQuery):
    parts = query.data.split("_", 2)
    is_video = parts[1] == "video"
    shortcode = parts[2]

    ig_url = f"https://www.instagram.com/reel/{shortcode}/"

    await query.answer("ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ...")

    status = await query.message.edit_text(
        "<blockquote>"
        f"⏳  ɪɴsᴛᴀɢʀᴀᴍ  {'ᴠɪᴅᴇᴏ' if is_video else 'ᴀᴜᴅɪᴏ'}  ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ...\n\n"
        f"🔗  <code>{ig_url}</code>"
        "</blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )

    file_path = None
    try:
        file_path = await download_instagram(ig_url, audio_only=not is_video)

        if not file_path or not os.path.exists(file_path):
            await status.edit_text(
                "<blockquote>"
                "❌  ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ\n\n"
                "ʀᴇᴇʟ ᴍᴀʏ ʙᴇ ᴘʀɪᴠᴀᴛᴇ ᴏʀ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ."
                "</blockquote>",
                parse_mode=enums.ParseMode.HTML,
            )
            return

        label = "ᴠɪᴅᴇᴏ" if is_video else "ᴀᴜᴅɪᴏ"
        await _send_file(query, status, file_path, is_video, "ɪɴsᴛᴀɢʀᴀᴍ", label)

    except Exception as e:
        logger.error(f"igdl error: {e}")
        try:
            await status.edit_text(
                f"<blockquote>❌  ᴇʀʀᴏʀ\n\n<code>{e}</code></blockquote>",
                parse_mode=enums.ParseMode.HTML,
            )
        except Exception:
            pass
    finally:
        _cleanup(file_path)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ꜱʜᴀʀᴇᴅ ʜᴇʟᴘᴇʀꜱ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def _send_file(
    query: CallbackQuery,
    status,
    file_path: str,
    is_video: bool,
    source: str,
    label: str,
):
    size_mb = os.path.getsize(file_path) / (1024 * 1024)

    if size_mb > 50:
        await status.edit_text(
            "<blockquote>"
            f"❌  ꜰɪʟᴇ ᴛᴏᴏ ʟᴀʀɢᴇ  ({size_mb:.1f} MB)\n\n"
            "ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ᴀᴘɪ ᴀʟʟᴏᴡꜱ ᴍᴀx  50 MB.\n"
            "ᴋᴏɪ ᴄʜᴏᴛɪ ʀᴇꜱᴏʟᴜᴛɪᴏɴ ᴛʀʏ ᴋᴀʀᴏ  (360ᴘ / 720ᴘ)"
            "</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    await status.edit_text(
        "<blockquote>"
        f"📤  ᴜᴘʟᴏᴀᴅɪɴɢ  {label}...\n\n"
        f"📦  <code>{size_mb:.1f} MB</code>"
        "</blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )

    caption = (
        "<blockquote>"
        f"{'🎬' if is_video else '🎵'}  {source}  —  {label}\n\n"
        f"📦  {size_mb:.1f} MB"
        "</blockquote>"
    )

    if is_video:
        await app.send_video(
            chat_id=query.message.chat.id,
            video=file_path,
            caption=caption,
            parse_mode=enums.ParseMode.HTML,
        )
    else:
        await app.send_audio(
            chat_id=query.message.chat.id,
            audio=file_path,
            caption=caption,
            parse_mode=enums.ParseMode.HTML,
        )

    await status.delete()


def _cleanup(file_path: str | None):
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"deleted: {file_path}")
        except Exception as e:
            logger.warning(f"delete failed: {e}")
