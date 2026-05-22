import os
import random
import pytz
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from Elevenyts import app

couple_cache = {}

COUPLE_IMAGES = [
    "https://drive.google.com/uc?export=download&id=1WGa6yNTXcAJPbCUA-n412gnKNyHt1rm_",
    "https://drive.google.com/uc?export=download&id=1K_w8ckNZFbhrCl_o-etPK_RSGxhMJApo",
    "https://drive.google.com/uc?export=download&id=1l0WE4IYXqNiKrY0lZhFHqvBpfcp19CyI",
    "https://drive.google.com/uc?export=download&id=1auUwGsx62_ThFIfGAjIjqYJLDY51qh0P",
    "https://drive.google.com/uc?export=download&id=1gA9LP_TCAFDNtKo33Q8PKBaUpCIq2vAD",
    "https://drive.google.com/uc?export=download&id=1hXemgpjndghquYHmtS0X0BkM0HE4S2Oh",
]

def get_today():
    tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(tz).strftime("%B %d, %Y")

def get_tomorrow():
    tz = pytz.timezone("Asia/Kolkata")
    return (datetime.now(tz) + timedelta(days=1)).strftime("%B %d, %Y")

def couple_text(mention1, mention2, today, tomorrow):
    return (
        f"<b>ᴄᴏᴜᴘʟᴇ ᴏғ ᴛʜᴇ ᴅᴀʏ</b>\n"
        f"────────────────────\n\n"
        f"⚡️ {mention1}\n"
        f"⚡️ {mention2}\n\n"
        f"<blockquote>"
        f"📅 <b>Timeline:</b> {today}\n"
        f"⏳ <b>Next Matchup:</b> {tomorrow}"
        f"</blockquote>"
    )

def couple_buttons(user1_id, name1, user2_id, name2):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text=f"✦ {name1}", url=f"tg://openmessage?user_id={user1_id}", style="success"),
            InlineKeyboardButton(text=f"✦ {name2}", url=f"tg://openmessage?user_id={user2_id}", style="danger"),
        ]
    ])


@app.on_message(filters.command(["couple", "couples"]) & ~filters.private)
async def couple_of_the_day(_, m: Message):
    chat_id  = m.chat.id
    today    = get_today()
    tomorrow = get_tomorrow()

    # Cache check
    cached = couple_cache.get(chat_id)
    if cached and cached["date"] == today:
        try:
            return await m.reply_photo(
                photo=cached["image"],
                caption=couple_text(cached["mention1"], cached["mention2"], today, tomorrow),
                reply_markup=couple_buttons(cached["id1"], cached["name1"], cached["id2"], cached["name2"])
            )
        except Exception:
            return await m.reply_text(
                text=couple_text(cached["mention1"], cached["mention2"], today, tomorrow),
                reply_markup=couple_buttons(cached["id1"], cached["name1"], cached["id2"], cached["name2"])
            )

    progress = await m.reply_text("✨ <code>Shuffling matchmaking matrix...</code>")

    # Members fetch
    try:
        members = []
        async for member in app.get_chat_members(chat_id, limit=100):
            if member.user and not member.user.is_bot and not member.user.is_deleted:
                members.append(member.user)
    except Exception as e:
        return await progress.edit_text(f"⚠️ <code>Error: {e}</code>")

    if len(members) < 2:
        return await progress.edit_text("⚠️ <code>Minimum 2 active members required.</code>")

    user1, user2 = random.sample(members, 2)
    name1 = user1.first_name[:15] if user1.first_name else "Anonymous"
    name2 = user2.first_name[:15] if user2.first_name else "Anonymous"

    mention1 = f"<a href='tg://openmessage?user_id={user1.id}'>{name1}</a>"
    mention2 = f"<a href='tg://openmessage?user_id={user2.id}'>{name2}</a>"

    selected_image = random.choice(COUPLE_IMAGES)

    couple_cache[chat_id] = {
        "date": today,
        "image": selected_image,
        "id1": user1.id,
        "name1": name1,
        "mention1": mention1,
        "id2": user2.id,
        "name2": name2,
        "mention2": mention2,
    }

    caption = couple_text(mention1, mention2, today, tomorrow)
    buttons = couple_buttons(user1.id, name1, user2.id, name2)

    await progress.delete()

    try:
        await m.reply_photo(
            photo=selected_image,
            caption=caption,
            reply_markup=buttons
        )
    except Exception:
        await m.reply_text(text=caption, reply_markup=buttons)


@app.on_message(filters.command(["couplereset"]) & ~filters.private)
async def reset_couple(_, m: Message):
    if m.chat.id in couple_cache:
        couple_cache.pop(m.chat.id)
        await m.reply_text("⚜️ <b>Matrix Reset:</b> Ready for a new selection.")
    else:
        await m.reply_text("⚠️ <code>No active matchup found for this session.</code>")
