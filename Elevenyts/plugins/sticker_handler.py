import os
import asyncio
from PIL import Image, ImageDraw, ImageFont
from pyrogram import filters, enums
from pyrogram.types import Message
from Elevenyts import app

_HERE      = os.path.dirname(os.path.abspath(__file__))
_HELPERS   = os.path.join(_HERE, "..", "..", "helpers")
FONT_BOLD  = os.path.join(_HELPERS, "Raleway-Bold.ttf")
FONT_LIGHT = os.path.join(_HELPERS, "Inter-Light.ttf")
FONT_SYS   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def _render_universal_sticker(content_text: str, is_sticker: bool, user_name: str, pfp_path: str | None, out_path: str):
    padding = 20
    avatar_size = 70
    max_width = 512
    bg_color = (24, 34, 45, 255)
    name_color = (82, 172, 232, 255)
    text_color = (255, 255, 255, 255)
    
    try:
        font_name = ImageFont.truetype(FONT_BOLD, 19)
        font_msg = ImageFont.truetype(FONT_LIGHT, 16)
    except IOError:
        font_name = ImageFont.truetype(FONT_SYS, 18)
        font_msg = ImageFont.truetype(FONT_SYS, 16)
        
    try:
        font_fallback = ImageFont.truetype(FONT_SYS, 16)
    except IOError:
        font_fallback = font_msg

    if is_sticker:
        content_text = "✨ [Sticker]"
        text_color = (130, 160, 180, 255)
        
    lines = []
    words = content_text.split()
    current_line = ""
    
    temp_img = Image.new("RGBA", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    available_width = max_width - avatar_size - (padding * 4)
    
    for word in words:
        test_line = f"{current_line} {word}".strip()
        w = temp_draw.textbbox((0, 0), test_line, font=font_msg)[2]
        if w <= available_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
        
    wrapped_text = "\n".join(lines)
    
    name_w, name_h = temp_draw.textbbox((0, 0), user_name, font=font_name)[2:4]
    text_w, text_h = temp_draw.textbbox((0, 0), wrapped_text, font=font_msg)[2:4]
    
    bubble_width = max(name_w, text_w) + (padding * 2)
    bubble_height = name_h + text_h + (padding * 2.5)
    
    canvas_w = avatar_size + bubble_width + (padding * 2)
    canvas_h = max(avatar_size, bubble_height) + (padding * 2)
    
    canvas = Image.new("RGBA", (int(canvas_w), int(canvas_h)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    pfp_x, pfp_y = padding, padding
    if pfp_path and os.path.exists(pfp_path):
        with Image.open(pfp_path) as pfp:
            pfp = pfp.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            canvas.paste(pfp, (pfp_x, pfp_y), mask=mask)
    else:
        draw.ellipse((pfp_x, pfp_y, pfp_x + avatar_size, pfp_y + avatar_size), fill=(43, 82, 120, 255))
        draw.text((pfp_x + 24, pfp_y + 18), user_name[0].upper(), fill=(255, 255, 255, 255), font=font_name)

    bx1 = pfp_x + avatar_size + 15
    by1 = padding
    bx2 = bx1 + bubble_width
    by2 = by1 + bubble_height
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=16, fill=bg_color)
    
    draw.text((bx1 + padding, by1 + padding), user_name, fill=name_color, font=font_name)
    
    try:
        draw.text((bx1 + padding, by1 + padding + name_h + 12), wrapped_text, fill=text_color, font=font_msg)
    except Exception:
        draw.text((bx1 + padding, by1 + padding + name_h + 12), wrapped_text, fill=text_color, font=font_fallback)
    
    canvas.thumbnail((512, 512), Image.Resampling.LANCZOS)
    canvas.save(out_path, "WEBP")


async def process_universal_sticker(message: Message) -> str | None:
    os.makedirs("cache", exist_ok=True)
    out_path = f"cache/quote_{message.id}.webp"
    
    user = message.from_user
    user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() if user else "User"
    if not user_name:
        user_name = "User"
        
    content_text = message.text or message.caption or ""
    is_sticker = bool(message.sticker)
    
    if not content_text and not is_sticker:
        content_text = "🖼️ [Media]"

    pfp_path = None
    if user and user.photo:
        try:
            pfp_path = await app.download_media(user.photo.big_file_id)  # ✅ Fixed
        except Exception:
            pfp_path = None
        
    try:
        await asyncio.to_thread(_render_universal_sticker, content_text, is_sticker, user_name, pfp_path, out_path)
        return out_path
    except Exception as e:
        print(f"[QuoteError]: {e}")
        return None
    finally:
        if pfp_path and os.path.exists(pfp_path):
            os.remove(pfp_path)


@app.on_message(filters.command(["q", "quotesticker"]) & (filters.group | filters.private))
async def universal_quote_cmd(_, message: Message):
    reply = message.reply_to_message
    
    if not reply:
        await message.reply_text("<blockquote>⚠️ Kisi message par reply karke `/q` likhein!</blockquote>", parse_mode=enums.ParseMode.HTML)
        return
        
    status = await message.reply_text("<blockquote>✍️ Quote bana raha hoon...</blockquote>", parse_mode=enums.ParseMode.HTML)
    sticker_path = await process_universal_sticker(reply)
    
    if sticker_path and os.path.exists(sticker_path):
        await message.reply_sticker(sticker_path)
        await status.delete()
        os.remove(sticker_path)
    else:
        await status.edit_text("<blockquote>❌ Sticker quote banane mein error aaya.</blockquote>", parse_mode=enums.ParseMode.HTML)
