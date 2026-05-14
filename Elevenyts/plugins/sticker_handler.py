import os
import asyncio
from PIL import Image, ImageFilter
from pyrogram import filters, enums
from pyrogram.types import Message
from Elevenyts import app


# ─────────────────────────── helpers ────────────────────────────

async def process_static_sticker(image_path: str) -> str | None:
    """Convert a static image → .webp sticker (512×512 max, white outline)."""
    os.makedirs("cache", exist_ok=True)
    sticker_path = f"cache/sticker_{os.path.basename(image_path)}.webp"
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGBA")
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)

            alpha   = img.getchannel("A")
            outline = alpha.filter(ImageFilter.MaxFilter(5))

            canvas   = Image.new("RGBA", img.size, (0, 0, 0, 0))
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            canvas.paste(white_bg, mask=outline)
            canvas.paste(img, (0, 0), mask=img)
            canvas.save(sticker_path, "WEBP")
        return sticker_path
    except Exception as e:
        print(f"[sticker] static error: {e}")
        return None


async def process_animated_sticker(media_path: str) -> str | None:
    """
    Convert a GIF or video → animated .webm sticker using ffmpeg.

    Telegram animated stickers must be:
      • WebM container  (VP9 video, no audio)
      • ≤ 512×512 px    (fit inside, keep aspect ratio)
      • ≤ 3 seconds     (Telegram hard limit for sticker packs, but bots can send longer)
      • Transparent bg kept if source has it (GIF palette → yuva420p)
    """
    os.makedirs("cache", exist_ok=True)
    out_path = f"cache/animated_{os.path.basename(media_path)}.webm"

    # Scale: fit inside 512×512 keeping aspect ratio, pad to even dimensions
    vf = (
        "scale='if(gt(iw,ih),512,trunc(512*iw/ih/2)*2)':"
        "'if(gt(ih,iw),512,trunc(512*ih/iw/2)*2)',"
        "fps=30"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", media_path,
        "-vf", vf,
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuva420p",   # keeps alpha channel (transparent bg for GIFs)
        "-b:v", "0",
        "-crf", "30",
        "-an",                    # no audio
        "-t", "10",               # cap at 10 s (adjust as needed)
        out_path,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            print(f"[sticker] ffmpeg error: {stderr.decode()}")
            return None
        return out_path
    except FileNotFoundError:
        print("[sticker] ffmpeg not found – install it: apt install ffmpeg")
        return None
    except Exception as e:
        print(f"[sticker] animated error: {e}")
        return None


def _is_animated(message: Message) -> bool:
    """Return True if the replied message contains a GIF/animation/video."""
    return bool(
        message.animation          # GIF / MP4-GIF (Telegram animation)
        or message.video           # regular video
        or message.video_note      # round video
    )


# ─────────────────────────── command ────────────────────────────

@app.on_message(
    filters.command(["sticker", "makesticker"])
    & (filters.group | filters.private)
)
async def sticker_cmd(_, message: Message):
    reply = message.reply_to_message

    # ── reply check ──────────────────────────────────────────────
    if not reply or not (reply.photo or _is_animated(reply)):
        await message.reply_text(
            "<blockquote>"
            "⚠️  ɪᴍᴀɢᴇ / ɢɪꜰ ɴᴏᴛ ꜰᴏᴜɴᴅ\n\n"
            "ʜᴏᴡ ᴛᴏ ᴜꜱᴇ :\n"
            "  ➊  ꜱᴇɴᴅ ᴀɴʏ ɪᴍᴀɢᴇ, ɢɪꜰ ᴏʀ ᴠɪᴅᴇᴏ\n"
            "  ➋  ʀᴇᴘʟʏ ᴛᴏ ɪᴛ ᴡɪᴛʜ  /sticker"
            "</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    animated = _is_animated(reply)

    status = await message.reply_text(
        "<blockquote>"
        + ("🎬  ᴀɴɪᴍᴀᴛᴇᴅ ꜱᴛɪᴄᴋᴇʀ ʙᴀɴ ʀʜᴀ ʜᴀɪ..." if animated
           else "🎨  ꜱᴛɪᴄᴋᴇʀ ʙᴀɴ ʀʜᴀ ʜᴀɪ...")
        + "</blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )

    media_path   = None
    sticker_path = None

    try:
        # Download whatever media is in the reply
        media_path = await reply.download()

        if animated:
            sticker_path = await process_animated_sticker(media_path)
        else:
            sticker_path = await process_static_sticker(media_path)

        if sticker_path:
            await message.reply_sticker(sticker_path)
            await status.delete()
        else:
            err_text = (
                "❌  ffmpeg ɪɴꜱᴛᴀʟ ɴʜɪ ʜᴀɪ ʏᴀ ᴄᴏɴᴠᴇʀꜱɪᴏɴ ꜰᴀɪʟ ʜᴏɢʏɪ."
                if animated else
                "❌  ꜱᴛɪᴄᴋᴇʀ ᴄᴏɴᴠᴇʀꜱɪᴏɴ ꜰᴀɪʟᴇᴅ."
            )
            await status.edit_text(
                f"<blockquote>{err_text}</blockquote>",
                parse_mode=enums.ParseMode.HTML,
            )

    except Exception as e:
        await status.edit_text(
            f"<blockquote>❌  ᴇʀʀᴏʀ\n\n<code>{e}</code></blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )

    finally:
        for path in (media_path, sticker_path):
            if path and os.path.exists(path):
                os.remove(path)
