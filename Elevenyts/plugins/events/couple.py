import random
import pytz
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from Elevenyts import app

couple_cache = {}

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
                photo=cached["pfp"],
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

    # Mention banao
    mention1 = f"<a href='tg://openmessage?user_id={user1.id}'>{name1}</a>"
    mention2 = f"<a href='tg://openmessage?user_id={user2.id}'>{name2}</a>"

    # User 1 ki profile photo download karo
    pfp_path = f"downloads/couple_pfp_{chat_id}.jpg"
    pfp_file = None
    import os
    os.makedirs("downloads", exist_ok=True)

    try:
        photos = await app.get_chat_photos(user1.id, limit=1)
        if photos:
            pfp_file = await app.download_media(photos[0].file_id, file_name=pfp_path)
    except Exception:
        pass

    # Cache save
    couple_cache[chat_id] = {
        "date": today,
        "pfp": pfp_file,       # None hoga agar photo nahi mili
        "id1": user1.id,
        "name1": name1,
        "mention1": mention1,
        "id2": user2.id,
        "name2": name2,
        "mention2": mention2,
    }

    caption = couple_text(mention1, mention2, today, tomorrow)
    buttons = couple_buttons(user1.id, name1, user2.id, name2)

    try:
        if pfp_file:
            await m.reply_photo(
                photo=pfp_file,
                caption=caption,
                reply_markup=buttons
            )
        else:
            await m.reply_text(text=caption, reply_markup=buttons)
    except Exception:
        await m.reply_text(text=caption, reply_markup=buttons)
    finally:
        # Local file delete karo
        try:
            if pfp_file:
                os.remove(pfp_file)
        except Exception:
            pass

    await progress.delete()


@app.on_message(filters.command(["couplereset"]) & ~filters.private)
async def reset_couple(_, m: Message):
    if m.chat.id in couple_cache:
        couple_cache.pop(m.chat.id)
        await m.reply_text("⚜️ <b>Matrix Reset:</b> Ready for a new selection.")
    else:
        await m.reply_text("⚠️ <code>No active matchup found for this session.</code>")
