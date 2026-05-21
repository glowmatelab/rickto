import os
import random
import requests
import pytz
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegraph import upload_file
from Elevenyts import app

couple_cache = {}  # {chat_id: {"date": "DD/MM/YYYY", "c1_id": int, "c2_id": int, "img_url": str}}

def get_today():
    tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(tz).strftime("%d/%m/%Y")

def get_tomorrow():
    tz = pytz.timezone("Asia/Kolkata")
    return (datetime.now(tz) + timedelta(days=1)).strftime("%d/%m/%Y")

def download_image(url, path):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
    except Exception:
        pass
    return path

DEFAULT_PFP = "https://drive.google.com/uc?id=1MXl7iZ0SoAp-SFdNMSj30LUDbg-ea-ac"
COUPLE_BG   = "https://drive.google.com/uc?id=1auUwGsx62_ThFIfGAjIjqYJLDY51qh0P"


async def make_and_upload(app, c1_id, c2_id, chat_id) -> str:
    """Image banao, Telegraph pe upload karo, local file delete karo, URL return karo."""
    os.makedirs("downloads", exist_ok=True)

    p1   = f"downloads/pfp1_{chat_id}.png"
    p2   = f"downloads/pfp2_{chat_id}.png"
    bg   = f"downloads/bg_{chat_id}.png"
    out  = f"downloads/couple_{chat_id}.png"

    # Profile photos
    try:
        photo1 = (await app.get_chat(c1_id)).photo
        await app.download_media(photo1.big_file_id, file_name=p1)
    except Exception:
        download_image(DEFAULT_PFP, p1)

    try:
        photo2 = (await app.get_chat(c2_id)).photo
        await app.download_media(photo2.big_file_id, file_name=p2)
    except Exception:
        download_image(DEFAULT_PFP, p2)

    download_image(COUPLE_BG, bg)

    # Image banaao
    img1 = Image.open(p1).convert("RGBA").resize((437, 437))
    img2 = Image.open(p2).convert("RGBA").resize((437, 437))
    background = Image.open(bg).convert("RGBA")

    def circle(img):
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + img.size, fill=255)
        img.putalpha(mask)
        return img

    background.paste(circle(img1), (116, 160), img1)
    background.paste(circle(img2), (789, 160), img2)
    background.save(out)

    # Telegraph upload
    uploaded = upload_file(out)
    img_url = "https://graph.org/" + uploaded[0]

    # Saari local files turant delete karo
    for f in [p1, p2, bg, out]:
        try:
            os.remove(f)
        except Exception:
            pass

    return img_url  # Sirf URL bachta hai


@app.on_message(filters.command(["couple", "couples"]) & ~filters.private)
async def couple_of_the_day(_, m: Message):
    chat_id  = m.chat.id
    today    = get_today()
    tomorrow = get_tomorrow()

    # Cache check
    cached = couple_cache.get(chat_id)
    if cached and cached["date"] == today:
        c1 = await app.get_users(cached["c1_id"])
        c2 = await app.get_users(cached["c2_id"])
        return await m.reply_photo(
            cached["img_url"],
            caption=(
                f"<b>💑 Tᴏᴅᴀʏ's Cᴏᴜᴘʟᴇ ᴏғ ᴛʜᴇ Dᴀʏ 🎉\n\n"
                f"{c1.mention} ❤️ {c2.mention}\n\n"
                f"📅 Nᴇxᴛ ᴄᴏᴜᴘʟᴇ ᴏɴ {tomorrow}!</b>"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Aᴅᴅ Mᴇ 🌋", url=f"https://t.me/{app.username}?startgroup=true")
            ]])
        )

    msg = await m.reply_text("❣️ Aaj ka couple dhundh raha hoon...")

    # Members fetch
    try:
        members = []
        async for member in app.get_chat_members(chat_id):
            if not member.user.is_bot and not member.user.is_deleted:
                members.append(member.user.id)
    except Exception as e:
        return await msg.edit_text(f"❌ Members fetch nahi hue!\n<code>{e}</code>")

    if len(members) < 2:
        return await msg.edit_text("❌ Kam se kam 2 real members chahiye!")

    c1_id, c2_id = random.sample(members, 2)

    # Image banao aur upload karo
    try:
        img_url = await make_and_upload(app, c1_id, c2_id, chat_id)
    except Exception as e:
        return await msg.edit_text(f"❌ Image error!\n<code>{e}</code>")

    # Sirf URL cache karo — koi file nahi
    couple_cache[chat_id] = {
        "date": today,
        "c1_id": c1_id,
        "c2_id": c2_id,
        "img_url": img_url,
    }

    c1 = await app.get_users(c1_id)
    c2 = await app.get_users(c2_id)

    await m.reply_photo(
        img_url,
        caption=(
            f"<b>💑 Tᴏᴅᴀʏ's Cᴏᴜᴘʟᴇ ᴏғ ᴛʜᴇ Dᴀʏ 🎉\n\n"
            f"{c1.mention} ❤️ {c2.mention}\n\n"
            f"📅 Nᴇxᴛ ᴄᴏᴜᴘʟᴇ ᴏɴ {tomorrow}!</b>"
        ),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Aᴅᴅ Mᴇ 🌋", url=f"https://t.me/{app.username}?startgroup=true")
        ]])
    )
    await msg.delete()


@app.on_message(filters.command(["couplereset"]) & ~filters.private)
async def reset_couple(_, m: Message):
    if m.chat.id in couple_cache:
        couple_cache.pop(m.chat.id)
        await m.reply_text("♻️ Couple reset! Ab naya choose hoga.")
    else:
        await m.reply_text("⚠️ Aaj ka koi couple set nahi tha.")
