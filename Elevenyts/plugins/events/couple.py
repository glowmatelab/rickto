import os
import random
import pytz
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from pyrogram import filters
from pyrogram.types import Message
from Elevenyts import app

couple_cache = {}

BACKGROUNDS = [
    "https://drive.google.com/uc?export=download&id=1WGa6yNTXcAJPbCUA-n412gnKNyHt1rm_",
    "https://drive.google.com/uc?export=download&id=1K_w8ckNZFbhrCl_o-etPK_RSGxhMJApo",
    "https://drive.google.com/uc?export=download&id=1l0WE4IYXqNiKrY0lZhFHqvBpfcp19CyI",
    "https://drive.google.com/uc?export=download&id=1auUwGsx62_ThFIfGAjIjqYJLDY51qh0P",
    "https://drive.google.com/uc?export=download&id=1gA9LP_TCAFDNtKo33Q8PKBaUpCIq2vAD",
    "https://drive.google.com/uc?export=download&id=1hXemgpjndghquYHmtS0X0BkM0HE4S2Oh",
]

def get_today():
    tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(tz).strftime("%d/%m/%Y")

def get_tomorrow():
    tz = pytz.timezone("Asia/Kolkata")
    return (datetime.now(tz) + timedelta(days=1)).strftime("%d/%m/%Y")

def download_image(url, path):
    try:
        session = requests.Session()
        r = session.get(url, timeout=15, allow_redirects=True)
        for key, value in r.cookies.items():
            if key.startswith("download_warning"):
                r = session.get(url + f"&confirm={value}", timeout=15)
                break
        if r.status_code == 200 and len(r.content) > 1000:
            with open(path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False


def make_couple_image(name1, name2, chat_id) -> str:
    os.makedirs("downloads", exist_ok=True)
    bg_path = f"downloads/bg_{chat_id}.png"
    out     = f"downloads/couple_{chat_id}.png"

    # Random background download
    bg_url = random.choice(BACKGROUNDS)
    ok = download_image(bg_url, bg_path)

    if ok:
        try:
            bg = Image.open(bg_path).convert("RGBA")
        except Exception:
            bg = Image.new("RGBA", (1280, 720), (30, 0, 50, 255))
    else:
        bg = Image.new("RGBA", (1280, 720), (30, 0, 50, 255))

    bg = bg.resize((1280, 720))
    draw = ImageDraw.Draw(bg)

    # Font — bot ke helpers folder mein jo fonts hain woh use karo
    try:
        font_big  = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 72)
        font_mid  = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 52)
        font_small = ImageFont.truetype("Elevenyts/helpers/Inter-Light.ttf", 36)
    except Exception:
        font_big  = ImageFont.load_default()
        font_mid  = font_big
        font_small = font_big

    W, H = bg.size

    # Title
    title = "💑 Couple of the Day"
    tb = draw.textbbox((0, 0), title, font=font_small)
    tw = tb[2] - tb[0]
    draw.text(((W - tw) // 2, 60), title, font=font_small, fill=(255, 255, 255, 220))

    # Name 1 — left side
    n1_bbox = draw.textbbox((0, 0), name1, font=font_big)
    n1_w = n1_bbox[2] - n1_bbox[0]
    draw.text(
        (W // 4 - n1_w // 2, H // 2 - 60),
        name1,
        font=font_big,
        fill=(255, 220, 220, 255),
    )

    # Heart — center
    heart_bbox = draw.textbbox((0, 0), "❤️", font=font_big)
    heart_w = heart_bbox[2] - heart_bbox[0]
    draw.text(
        (W // 2 - heart_w // 2, H // 2 - 60),
        "❤️",
        font=font_big,
        fill=(255, 80, 80, 255),
    )

    # Name 2 — right side
    n2_bbox = draw.textbbox((0, 0), name2, font=font_big)
    n2_w = n2_bbox[2] - n2_bbox[0]
    draw.text(
        (W * 3 // 4 - n2_w // 2, H // 2 - 60),
        name2,
        font=font_big,
        fill=(220, 220, 255, 255),
    )

    # Date bottom
    date_text = f"📅 {get_today()}"
    db = draw.textbbox((0, 0), date_text, font=font_small)
    dw = db[2] - db[0]
    draw.text(((W - dw) // 2, H - 80), date_text, font=font_small, fill=(255, 255, 255, 180))

    bg.save(out)

    try:
        os.remove(bg_path)
    except Exception:
        pass

    return out


@app.on_message(filters.command(["couple", "couples"]) & ~filters.private)
async def couple_of_the_day(_, m: Message):
    chat_id  = m.chat.id
    today    = get_today()
    tomorrow = get_tomorrow()

    # Cache check
    cached = couple_cache.get(chat_id)
    if cached and cached["date"] == today:
        return await m.reply_photo(
            cached["file_id"],
            caption=(
                f"💑 <b>Couple of the Day!</b>\n\n"
                f"❤️ {cached['name1']}\n"
                f"🩷 {cached['name2']}\n\n"
                f"<i>📅 Next couple on {tomorrow}!</i>"
            )
        )

    msg = await m.reply_text("❣️ Aaj ka couple dhundh raha hoon...")

    # Members fetch
    try:
        members = []
        async for member in app.get_chat_members(chat_id):
            if not member.user.is_bot and not member.user.is_deleted:
                members.append(member.user)
    except Exception as e:
        return await msg.edit_text(f"❌ Members fetch nahi hue!\n<code>{e}</code>")

    if len(members) < 2:
        return await msg.edit_text("❌ Kam se kam 2 real members chahiye!")

    user1, user2 = random.sample(members, 2)
    name1 = user1.first_name[:15]  # Long names trim karo
    name2 = user2.first_name[:15]

    # Image banao
    try:
        img_path = make_couple_image(name1, name2, chat_id)
    except Exception as e:
        return await msg.edit_text(f"❌ Image error!\n<code>{e}</code>")

    caption = (
        f"💑 <b>Couple of the Day!</b>\n\n"
        f"❤️ {user1.mention}\n"
        f"🩷 {user2.mention}\n\n"
        f"<i>📅 Next couple on {tomorrow}!</i>"
    )

    try:
        sent = await m.reply_photo(img_path, caption=caption)
        file_id = sent.photo.file_id
    except Exception as e:
        return await msg.edit_text(f"❌ Send error!\n<code>{e}</code>")
    finally:
        try:
            os.remove(img_path)
        except Exception:
            pass

    couple_cache[chat_id] = {
        "date": today,
        "file_id": file_id,
        "name1": user1.mention,
        "name2": user2.mention,
    }

    await msg.delete()


@app.on_message(filters.command(["couplereset"]) & ~filters.private)
async def reset_couple(_, m: Message):
    if m.chat.id in couple_cache:
        couple_cache.pop(m.chat.id)
        await m.reply_text("♻️ Reset! Ab naya couple choose hoga.")
    else:
        await m.reply_text("⚠️ Koi couple set nahi tha.")
