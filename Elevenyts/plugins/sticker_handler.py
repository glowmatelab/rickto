import os
import asyncio
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pyrogram import filters, enums
from pyrogram.types import Message
from Elevenyts import app


# ═══════════════════════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════════════════════

_HERE      = os.path.dirname(os.path.abspath(__file__))
_HELPERS   = os.path.join(_HERE, "..", "..", "helpers")
FONT_BOLD  = os.path.join(_HELPERS, "Raleway-Bold.ttf")
FONT_LIGHT = os.path.join(_HELPERS, "Inter-Light.ttf")
FONT_SYS   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


# ═══════════════════════════════════════════════════════════════
#  QUOTE CARD RENDERER
# ═══════════════════════════════════════════════════════════════

# ── palette (Telegram dark theme) ──
_BG       = (33,  33,  44,  255)
_CARD     = (30,  30,  42,  245)
_REPLY_BG = (40,  40,  56,  220)
_BORDER   = (100, 160, 255, 255)   # blue left-border on reply
_TXT      = (230, 230, 230, 255)
_REPLY_TXT= (170, 170, 200, 255)

_NAME_COLORS = [
    (255, 120, 120), (120, 200, 255), (120, 255, 180),
    (255, 200, 100), (200, 120, 255), (255, 160,  80),
]


def _name_color(name: str) -> tuple:
    return _NAME_COLORS[sum(ord(c) for c in name) % len(_NAME_COLORS)]


def _make_avatar(name: str, size: int = 60) -> Image.Image:
    """Coloured circle with the first letter of the name."""
    color = _name_color(name)
    img   = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size - 1, size - 1], fill=(*color, 255))
    try:
        font = ImageFont.truetype(FONT_BOLD, size // 2)
    except Exception:
        font = ImageFont.load_default()
    letter = (name[0].upper()) if name else "?"
    bb = draw.textbbox((0, 0), letter, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text(
        ((size - tw) // 2, (size - th) // 2 - 2),
        letter, font=font, fill=(20, 20, 30, 255),
    )
    return img


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    """Word-wrap text to fit inside max_w pixels."""
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def _load_fonts(sizes: dict) -> dict:
    fonts = {}
    for key, (path, sz) in sizes.items():
        try:
            fonts[key] = ImageFont.truetype(path, sz)
        except Exception:
            fonts[key] = ImageFont.load_default()
    return fonts


def make_quote_image(
    sender_name:  str,
    message_text: str,
    reply_sender: str  = None,
    reply_text:   str  = None,
    avatar_img:   Image.Image = None,   # optional real profile pic
) -> Image.Image:
    """
    Render a Telegram-style dark quote card and return an RGBA Image.

    Layout
    ──────
    ┌──────────────────────────────────────┐
    │ [avatar]  SenderName                 │
    │           ┌─ reply box (optional) ──┐│
    │           │ ReplyUser               ││
    │           │ reply text...           ││
    │           └────────────────────────┘│
    │           main message text...      │
    └──────────────────────────────────────┘
    """

    PAD       = 24
    AVATAR_SZ = 60
    MAX_CARD  = 460          # max card width
    NAME_SZ   = 26
    TEXT_SZ   = 22
    R_SZ      = 18           # reply box font size
    LINE_GAP  = 6

    fonts = _load_fonts({
        "name" : (FONT_BOLD,  NAME_SZ),
        "text" : (FONT_SYS,   TEXT_SZ),
        "rname": (FONT_BOLD,  R_SZ),
        "rtxt" : (FONT_SYS,   R_SZ),
    })

    dummy = Image.new("RGBA", (1, 1))
    d     = ImageDraw.Draw(dummy)

    text_w = MAX_CARD - AVATAR_SZ - PAD * 3   # width available for text

    main_lines  = _wrap(d, message_text, fonts["text"], text_w)
    reply_lines = []
    if reply_text:
        reply_lines = _wrap(d, reply_text, fonts["rtxt"], text_w - 18)[:4]

    # ── height calculation ──
    reply_box_h = 0
    if reply_lines:
        reply_box_h = (
            PAD // 2            # inner top pad
            + R_SZ + 4          # reply sender name
            + len(reply_lines) * (R_SZ + 4)   # reply text lines
            + PAD // 2          # inner bottom pad
            + 8                 # gap below box
        )

    content_h = (
        PAD
        + NAME_SZ + 8
        + reply_box_h
        + len(main_lines) * (TEXT_SZ + LINE_GAP)
        + PAD
    )
    card_h = max(content_h, AVATAR_SZ + PAD * 2)
    card_w = MAX_CARD + PAD * 2

    # ── canvas ──
    img  = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=20, fill=_CARD)

    # ── avatar ──
    av = avatar_img if avatar_img else _make_avatar(sender_name, AVATAR_SZ)
    # crop to circle if real photo
    if avatar_img:
        av = av.resize((AVATAR_SZ, AVATAR_SZ), Image.Resampling.LANCZOS).convert("RGBA")
        mask = Image.new("L", (AVATAR_SZ, AVATAR_SZ), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, AVATAR_SZ - 1, AVATAR_SZ - 1], fill=255)
        av.putalpha(mask)
    img.paste(av, (PAD, PAD), mask=av)

    # ── text origin ──
    tx = PAD + AVATAR_SZ + PAD
    ty = PAD

    # sender name
    name_col = _name_color(sender_name)
    draw.text((tx, ty), sender_name, font=fonts["name"], fill=(*name_col, 255))
    ty += NAME_SZ + 8

    # reply quote box
    if reply_lines:
        bx1, by1 = tx, ty
        bx2      = tx + text_w
        by2      = ty + reply_box_h - 8
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=10, fill=_REPLY_BG)
        draw.rounded_rectangle([bx1, by1, bx1 + 3, by2], radius=2, fill=_BORDER)

        ry = by1 + PAD // 2
        draw.text((bx1 + 14, ry), reply_sender or "Unknown",
                  font=fonts["rname"], fill=_BORDER)
        ry += R_SZ + 4
        for line in reply_lines:
            draw.text((bx1 + 14, ry), line, font=fonts["rtxt"], fill=_REPLY_TXT)
            ry += R_SZ + 4
        ty = by2 + 10

    # main text
    for line in main_lines:
        draw.text((tx, ty), line, font=fonts["text"], fill=_TXT)
        ty += TEXT_SZ + LINE_GAP

    return img


# ═══════════════════════════════════════════════════════════════
#  STATIC STICKER HELPER  (existing)
# ═══════════════════════════════════════════════════════════════

async def process_static_sticker(image_path: str) -> str | None:
    """Convert a static image → .webp sticker (512×512 max, white outline)."""
    os.makedirs("cache", exist_ok=True)
    sticker_path = f"cache/sticker_{os.path.basename(image_path)}.webp"
    try:
        with Image.open(image_path) as img:
            img     = img.convert("RGBA")
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            alpha   = img.getchannel("A")
            outline = alpha.filter(ImageFilter.MaxFilter(5))
            canvas  = Image.new("RGBA", img.size, (0, 0, 0, 0))
            white   = Image.new("RGBA", img.size, (255, 255, 255, 255))
            canvas.paste(white, mask=outline)
            canvas.paste(img, (0, 0), mask=img)
            canvas.save(sticker_path, "WEBP")
        return sticker_path
    except Exception as e:
        print(f"[sticker] static error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
#  ANIMATED STICKER HELPER  (existing)
# ═══════════════════════════════════════════════════════════════

async def process_animated_sticker(media_path: str) -> str | None:
    """Convert GIF/video → animated .webm sticker via ffmpeg."""
    os.makedirs("cache", exist_ok=True)
    out_path = f"cache/animated_{os.path.basename(media_path)}.webm"
    vf = (
        "scale='if(gt(iw,ih),512,trunc(512*iw/ih/2)*2)':"
        "'if(gt(ih,iw),512,trunc(512*ih/iw/2)*2)',"
        "fps=30"
    )
    cmd = [
        "ffmpeg", "-y", "-i", media_path,
        "-vf", vf,
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuva420p",
        "-b:v", "0", "-crf", "30", "-an", "-t", "10",
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
        print("[sticker] ffmpeg not found")
        return None
    except Exception as e:
        print(f"[sticker] animated error: {e}")
        return None


def _is_animated(message: Message) -> bool:
    return bool(message.animation or message.video or message.video_note)


# ═══════════════════════════════════════════════════════════════
#  /q  —  QUOTE STICKER
# ═══════════════════════════════════════════════════════════════

@app.on_message(
    filters.command("q") & (filters.group | filters.private)
)
async def quote_cmd(client, message: Message):
    reply = message.reply_to_message

    # must be a reply to a text message
    if not reply or not reply.text:
        await message.reply_text(
            "<blockquote>"
            "⚠️  <b>Kisi text message pe reply karke /q bhejo!</b>\n\n"
            "Usage :\n"
            "  • Kisi bhi text message pe reply karo\n"
            "  • /q likho\n"
            "  • Bot us message ka sticker bana dega 🎨"
            "</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    status = await message.reply_text(
        "<blockquote>🎨  <b>Quote sticker ban raha hai...</b></blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )

    sticker_path = None
    avatar_path  = None

    try:
        # ── sender info ──
        sender = reply.from_user
        sender_name = "Unknown"
        if sender:
            sender_name = sender.first_name or ""
            if sender.last_name:
                sender_name += f" {sender.last_name}"
            sender_name = sender_name.strip() or "Unknown"

        # ── try to download profile photo ──
        avatar_img = None
        try:
            if sender:
                avatar_path = await client.download_media(
                    sender.photo.big_file_id
                    if hasattr(sender, "photo") and sender.photo else None
                )
                if avatar_path:
                    avatar_img = Image.open(avatar_path).convert("RGBA")
        except Exception:
            avatar_img = None   # fallback to initial-letter avatar

        # ── reply-to-reply info (nested quote) ──
        reply_sender = None
        reply_text   = None
        if reply.reply_to_message and reply.reply_to_message.text:
            nested = reply.reply_to_message
            ru     = nested.from_user
            if ru:
                reply_sender = ru.first_name or "Unknown"
            reply_text = nested.text

        # ── render card ──
        card = make_quote_image(
            sender_name  = sender_name,
            message_text = reply.text,
            reply_sender = reply_sender,
            reply_text   = reply_text,
            avatar_img   = avatar_img,
        )

        # ── fit inside 512×512 (Telegram sticker limit) ──
        card.thumbnail((512, 512), Image.Resampling.LANCZOS)

        os.makedirs("cache", exist_ok=True)
        sticker_path = f"cache/quote_{reply.id}.webp"
        card.save(sticker_path, "WEBP", quality=95)

        await message.reply_sticker(sticker_path)
        await status.delete()

    except Exception as e:
        await status.edit_text(
            f"<blockquote>❌  <b>Error</b>\n\n<code>{e}</code></blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )

    finally:
        for path in (sticker_path, avatar_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass


# ═══════════════════════════════════════════════════════════════
#  /sticker  —  IMAGE / GIF → STICKER  (existing)
# ═══════════════════════════════════════════════════════════════

@app.on_message(
    filters.command(["sticker", "makesticker"])
    & (filters.group | filters.private)
)
async def sticker_cmd(_, message: Message):
    reply = message.reply_to_message

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
    status   = await message.reply_text(
        "<blockquote>"
        + ("🎬  ᴀɴɪᴍᴀᴛᴇᴅ ꜱᴛɪᴄᴋᴇʀ ʙᴀɴ ʀʜᴀ ʜᴀɪ..."
           if animated else "🎨  ꜱᴛɪᴄᴋᴇʀ ʙᴀɴ ʀʜᴀ ʜᴀɪ...")
        + "</blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )

    media_path   = None
    sticker_path = None

    try:
        media_path = await reply.download()
        if animated:
            sticker_path = await process_animated_sticker(media_path)
        else:
            sticker_path = await process_static_sticker(media_path)

        if sticker_path:
            await message.reply_sticker(sticker_path)
            await status.delete()
        else:
            err = (
                "❌  ffmpeg ɪɴꜱᴛᴀʟ ɴʜɪ ʜᴀɪ ʏᴀ ᴄᴏɴᴠᴇʀꜱɪᴏɴ ꜰᴀɪʟ ʜᴏɢʏɪ."
                if animated else
                "❌  ꜱᴛɪᴄᴋᴇʀ ᴄᴏɴᴠᴇʀꜱɪᴏɴ ꜰᴀɪʟᴇᴅ."
            )
            await status.edit_text(
                f"<blockquote>{err}</blockquote>",
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
