import os
import asyncio
from PIL import Image, ImageDraw, ImageFont
from pyrogram import filters, enums
from pyrogram.types import Message
from Elevenyts import app

# ─────────────────────────── font setup ────────────────────────────

_HERE      = os.path.dirname(os.path.abspath(__file__))
_HELPERS   = os.path.join(_HERE, "..", "..", "helpers")
FONT_BOLD  = os.path.join(_HELPERS, "Raleway-Bold.ttf")
FONT_LIGHT = os.path.join(_HELPERS, "Inter-Light.ttf")
FONT_SYS   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ─────────────────────────── helper ────────────────────────────

def _render_universal_sticker(
    content_text: str, 
    is_sticker: bool, 
    user_name: str, 
    pfp_path: str | None, 
    out_path: str,
    reply_name: str | None = None,
    reply_text: str | None = None
):
    padding = 20
    avatar_size = 70
    max_width = 512
    bg_color = (24, 34, 45, 255)       # Telegram Dark Mode Bubble
    name_color = (82, 172, 232, 255)   # Premium Telegram Blue
    text_color = (255, 255, 255, 255)  # White text
    reply_bar_color = (82, 172, 232, 255) # Reply vertical line
    reply_bg_color = (32, 46, 60, 255)   # Slightly lighter dark for reply box
    
    try:
        font_name = ImageFont.truetype(FONT_BOLD, 19)
        font_msg = ImageFont.truetype(FONT_LIGHT, 16)
        font_reply_name = ImageFont.truetype(FONT_BOLD, 15)
        font_reply_text = ImageFont.truetype(FONT_LIGHT, 14)
    except IOError:
        font_name = ImageFont.truetype(FONT_SYS, 18)
        font_msg = ImageFont.truetype(FONT_SYS, 16)
        font_reply_name = ImageFont.truetype(FONT_SYS, 15)
        font_reply_text = ImageFont.truetype(FONT_SYS, 14)
        
    try:
        font_fallback = ImageFont.truetype(FONT_SYS, 16)
    except IOError:
        font_fallback = font_msg

    if is_sticker:
        content_text = "✨ [Sticker]"
        text_color = (130, 160, 180, 255)

    # 1. Text Wrapping Logic
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
    
    # 2. Reply Context Calculations (Agar `/q r` use hua ho)
    has_reply = bool(reply_name and reply_text)
    reply_box_w, reply_box_h = 0, 0
    
    if has_reply:
        # Single line preview logic for reply context
        if len(reply_text) > 35:
            reply_text = reply_text[:32] + "..."
        rn_w = temp_draw.textbbox((0, 0), reply_name, font=font_reply_name)[2]
        rt_w = temp_draw.textbbox((0, 0), reply_text, font=font_reply_text)[2]
        reply_box_w = max(rn_w, rt_w) + 30
        reply_box_h = 45  # Fixed compact height for reply banner

    # 3. Total Dimension Calculations
    name_w, name_h = temp_draw.textbbox((0, 0), user_name, font=font_name)[2:4]
    text_w, text_h = temp_draw.textbbox((0, 0), wrapped_text, font=font_msg)[2:4]
    
    bubble_width = max(name_w, text_w, reply_box_w) + (padding * 2)
    
    if has_reply:
        bubble_height = name_h + reply_box_h + text_h + (padding * 3.5)
    else:
        bubble_height = name_h + text_h + (padding * 2.5)
        
    canvas_w = avatar_size + bubble_width + (padding * 2)
    canvas_h = max(avatar_size, bubble_height) + (padding * 2)
    
    canvas = Image.new("RGBA", (int(canvas_w), int(canvas_h)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # 4. Draw Profile Picture
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

    # 5. Draw Rounded Message Bubble
    bx1 = pfp_x + avatar_size + 15
    by1 = padding
    bx2 = bx1 + bubble_width
    by2 = by1 + bubble_height
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=16, fill=bg_color)
    
    # 6. Draw Sender Name
    current_y = by1 + padding
    draw.text((bx1 + padding, current_y), user_name, fill=name_color, font=font_name)
    current_y += name_h + 10

    # 7. Draw Reply Box Block (If active)
    if has_reply:
        rx1 = bx1 + padding
        ry1 = current_y
        rx2 = rx1 + max(name_w, text_w, reply_box_w) - 10
        ry2 = ry1 + reply_box_h
        
        # Background layer & accent vertical line
        draw.rectangle([rx1, ry1, rx2, ry2], fill=reply_bg_color)
        draw.rectangle([rx1, ry1, rx1 + 4, ry2], fill=reply_bar_color)
        
        # Texts inside reply structure
        draw.text((rx1 + 12, ry1 + 4), reply_name, fill=name_color, font=font_reply_name)
        draw.text((rx1 + 12, ry1 + 22), reply_text, fill=(170, 190, 200, 255), font=font_reply_text)
        current_y += reply_box_h + 12

    # 8. Draw Main Message Body
    try:
        draw.text((bx1 + padding, current_y), wrapped_text, fill=text_color, font=font_msg)
    except Exception:
        draw.text((bx1 + padding, current_y), wrapped_text, fill=text_color, font=font_fallback)
    
    # Save standard sticker resolution
    canvas.thumbnail((512, 512), Image.Resampling.LANCZOS)
    canvas.save(out_path, "WEBP")


async def process_universal_sticker(message: Message, include_reply: bool = False) -> str | None:
    os.makedirs("cache", exist_ok=True)
    out_path = f"cache/quote_{message.id}.webp"
    
    # User Details & Real-time PFP Fix Fetching
    user_id = message.from_user.id if message.from_user else None
    user_name = "User"
    pfp_path = None

    if user_id:
        try:
            full_user = await message.app.get_users(user_id)
            user_name = f"{full_user.first_name or ''} {full_user.last_name or ''}".strip() or "User"
            if full_user.photo:
                pfp_path = await message.app.download_media(full_user.photo.big_file_id)
        except Exception:
            user = message.from_user
            user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "User"

    content_text = message.text or message.caption or ""
    is_sticker = bool(message.sticker)
    if not content_text and not is_sticker:
        content_text = "🖼️ [Media]"

    # Handle Sub-Reply Context parsing
    reply_name, reply_text = None, None
    if include_reply and message.reply_to_message:
        rep = message.reply_to_message
        r_user = rep.from_user
        reply_name = f"{r_user.first_name or ''} {r_user.last_name or ''}".strip() if r_user else "User"
        
        if rep.text or rep.caption:
            reply_text = rep.text or rep.caption
        elif rep.sticker:
            reply_text = "✨ [Sticker]"
        else:
            reply_text = "🖼️ [Media]"

    try:
        await asyncio.to_thread(
            _render_universal_sticker, 
            content_text, is_sticker, user_name, pfp_path, out_path,
            reply_name, reply_text
        )
        return out_path
    except Exception as e:
        print(f"[QuoteError]: {e}")
        return None
    finally:
        if pfp_path and os.path.exists(pfp_path):
            try:
                os.remove(pfp_path)
            except Exception:
                pass


# ─────────────────────────── Command ────────────────────────────

@app.on_message(filters.command(["q", "quotesticker"]) & (filters.group | filters.private))
async def universal_quote_cmd(_, message: Message):
    reply = message.reply_to_message
    
    if not reply:
        await message.reply_text("<blockquote>⚠️ Kisi message par reply karke `/q` ya `/q r` likhein!</blockquote>", parse_mode=enums.ParseMode.HTML)
        return
        
    status = await message.reply_text("<blockquote>✍️ Quote bana raha hoon...</blockquote>", parse_mode=enums.ParseMode.HTML)
    
    # Agar user ne `/q r` ya `/q R` bheja ho argument me
    include_reply = False
    if len(message.command) > 1 and message.command[1].lower() == "r":
        include_reply = True

    # Main conversion call
    sticker_path = await process_universal_sticker(reply, include_reply=include_reply)
    
    if sticker_path and os.path.exists(sticker_path):
        await message.reply_sticker(sticker_path)
        await status.delete()
        try:
            os.remove(sticker_path)
        except Exception:
            pass
    else:
        await status.edit_text("<blockquote>❌ Sticker quote banane mein error aaya.</blockquote>", parse_mode=enums.ParseMode.HTML)
