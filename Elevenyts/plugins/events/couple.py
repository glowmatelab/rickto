import random
import pytz
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from Elevenyts import app

# In-memory cache for couples
couple_cache = {}

def get_today():
    tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(tz).strftime("%B %d, %Y")

def get_tomorrow():
    tz = pytz.timezone("Asia/Kolkata")
    return (datetime.now(tz) + timedelta(days=1)).strftime("%B %d, %Y")

def couple_text(name1, name2, today, tomorrow):
    return (
        f"<b>ᴄᴏᴜᴘʟᴇ ᴏғ ᴛʜᴇ ᴅᴀʏ</b>\n"
        f"────────────────────\n\n"
        f"⚡️ <b>{name1}</b>\n"
        f"⚡️ <b>{name2}</b>\n\n"
        f"<blockquote>"
        f"📅 <b>Timeline:</b> {today}\n"
        f"⏳ <b>Next Matchup:</b> {tomorrow}"
        f"</blockquote>"
    )

def couple_buttons(user1_id, name1, user2_id, name2):
    return InlineKeyboardMarkup([
        [
            # Success Style (Green)
            InlineKeyboardButton(
                text=f"✦ {name1}", 
                url=f"tg://openmessage?user_id={user1_id}",
                style="success"
            ),
            # Danger Style (Red)
            InlineKeyboardButton(
                text=f"✦ {name2}", 
                url=f"tg://openmessage?user_id={user2_id}",
                style="danger"
            ),
        ]
    ])


@app.on_message(filters.command(["couple", "couples"]) & ~filters.private)
async def couple_of_the_day(_, m: Message):
    chat_id  = m.chat.id
    today    = get_today()
    tomorrow = get_tomorrow()

    # Check Cache
    cached = couple_cache.get(chat_id)
    if cached and cached["date"] == today:
        return await m.reply_text(
            text=couple_text(cached["name1"], cached["name2"], today, tomorrow),
            reply_markup=couple_buttons(
                cached["id1"], cached["name1"],
                cached["id2"], cached["name2"],
            )
        )

    # Status message to check if command is triggering
    progress = await m.reply_text("✨ <code>Shuffling matchmaking matrix...</code>")
    
    try:
        members = []
        # Limit 100 rakha hai taaki performance fast rahe
        async for member in app.get_chat_members(chat_id, limit=100):
            if member.user and not member.user.is_bot and not member.user.is_deleted:
                members.append(member.user)
    except Exception as e:
        return await progress.edit_text(
            f"⚠️ <code>Error fetching members: {e}</code>\n\n"
            f"<i>Check karo bot group me Admin hai ya nahi!</i>"
        )

    if len(members) < 2:
        return await progress.edit_text("⚠️ <code>Minimum 2 active members required.</code>")

    # Select random couple
    user1, user2 = random.sample(members, 2)
    name1 = user1.first_name[:15] if user1.first_name else "Anonymous"
    name2 = user2.first_name[:15] if user2.first_name else "Anonymous"

    # Save to Cache
    couple_cache[chat_id] = {
        "date": today,
        "id1": user1.id,
        "name1": name1,
        "id2": user2.id,
        "name2": name2,
    }

    # Delete progress message and send final result
    await progress.delete()
    await m.reply_text(
        text=couple_text(name1, name2, today, tomorrow),
        reply_markup=couple_buttons(user1.id, name1, user2.id, name2)
    )


@app.on_message(filters.command(["couplereset"]) & ~filters.private)
async def reset_couple(_, m: Message):
    if m.chat.id in couple_cache:
        couple_cache.pop(m.chat.id)
        await m.reply_text("⚜️ <b>Matrix Reset:</b> Ready for a new selection.")
    else:
        await m.reply_text("⚠️ <code>No active matchup found for this session.</code>")
