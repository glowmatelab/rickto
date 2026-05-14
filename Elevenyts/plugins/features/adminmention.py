import asyncio
import re
from pyrogram import filters, types, enums
from Elevenyts import app, config

# Pattern to detect admin triggers
TRIGGER_PATTERN = re.compile(r"(?i)(\.|@|\/)admin")

# ─────────────────────────────────────────────
#  ADMIN MENTION  →  .admin / @admin / /admin
# ─────────────────────────────────────────────
@app.on_message(filters.group & filters.regex(r"(?i)(\.|@|\/)admin"))
async def mention_admins(_, message: types.Message):
    """
    Mention all group admins when someone types @admin, .admin, or /admin
    """
    try:
        message_text = message.text or message.caption or ""
        cleaned_text = TRIGGER_PATTERN.sub("", message_text).strip()

        sender = message.from_user
        if sender:
            user_display = f"{sender.first_name}"
            if sender.username:
                user_display += f" (@{sender.username})"
        else:
            user_display = "ᴀɴᴏɴʏᴍᴏᴜꜱ ᴀᴅᴍɪɴ"

        if cleaned_text:
            reply_msg = (
                f"<blockquote><b><i>\"{cleaned_text}\"</i></b>\n"
                f"ʀᴇᴘᴏʀᴛᴇᴅ ʙʏ: {user_display} 🔔</blockquote>\n\n"
            )
        else:
            reply_msg = (
                f"<blockquote>ʀᴇᴘᴏʀᴛᴇᴅ ʙʏ: {user_display} 🔔</blockquote>\n\n"
            )

        mentions = []
        try:
            async for admin in app.get_chat_members(
                message.chat.id,
                filter=enums.ChatMembersFilter.ADMINISTRATORS
            ):
                user = admin.user
                if user.is_bot or user.is_deleted:
                    continue
                if hasattr(admin, 'privileges') and admin.privileges:
                    if getattr(admin.privileges, 'is_anonymous', False):
                        continue
                if user.username and user.username.lower() in [u.lower() for u in config.EXCLUDED_USERNAMES]:
                    continue
                if user.username:
                    mentions.append(f"@{user.username}")
                else:
                    mentions.append(f"<a href='tg://user?id={user.id}'>{user.first_name}</a>")
        except Exception:
            await message.reply_text(
                "<blockquote>❌ Failed to fetch administrators. Make sure the bot has proper permissions.</blockquote>"
            )
            return

        if mentions:
            reply_msg += ", ".join(mentions)
        else:
            reply_msg += "<i>No visible human admins found to mention.</i>"

        try:
            await message.reply_text(reply_msg, disable_web_page_preview=True)
        except Exception:
            await message.reply_text(
                "<blockquote>❌ Failed to send admin notification.</blockquote>"
            )

    except Exception:
        try:
            await message.reply_text("<blockquote>❌ An error occurred while processing admin mention.</blockquote>")
        except:
            pass


# ─────────────────────────────────────────────
#  TAG ALL MEMBERS  →  /tagall
# ─────────────────────────────────────────────
BATCH_SIZE = 5       # kitne mentions ek message mein
DELAY      = 1.5     # seconds between batches (flood se bachne ke liye)

@app.on_message(filters.group & filters.command("tagall"))
async def tag_all_members(_, message: types.Message):
    """
    /tagall  – group ke saare human members ko mention karta hai
    Sirf admins use kar sakte hain.
    """
    try:
        # ── Admin check ──────────────────────────────────────────────
        sender = message.from_user
        if not sender:
            await message.reply_text("<blockquote>❌ Anonymous admins ye command use nahi kar sakte.</blockquote>")
            return

        member = await app.get_chat_member(message.chat.id, sender.id)
        allowed_statuses = (
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        )
        if member.status not in allowed_statuses:
            await message.reply_text("<blockquote>⛔ Sirf admins /tagall use kar sakte hain.</blockquote>")
            return

        # ── Optional custom message ──────────────────────────────────
        # /tagall Hello everyone!  →  "Hello everyone!" caption ke saath
        extra_text = ""
        if message.text and len(message.text.split(None, 1)) > 1:
            extra_text = message.text.split(None, 1)[1].strip()

        header = (
            f"<blockquote>📢 <b>TAG ALL</b>\n"
            f"ʙʏ: {sender.first_name}"
            + (f" (@{sender.username})" if sender.username else "")
            + (f"\n<i>{extra_text}</i>" if extra_text else "")
            + "</blockquote>\n\n"
        )

        # ── Collect all human members ────────────────────────────────
        status_msg = await message.reply_text("<blockquote>⏳ Members fetch ho rahe hain…</blockquote>")

        mentions = []
        try:
            async for member in app.get_chat_members(message.chat.id):
                user = member.user
                if user.is_bot or user.is_deleted:
                    continue
                if user.username:
                    mentions.append(f"@{user.username}")
                else:
                    mentions.append(f"<a href='tg://user?id={user.id}'>{user.first_name}</a>")
        except Exception:
            await status_msg.edit_text(
                "<blockquote>❌ Members fetch karne mein error. Bot ko admin banana check karo.</blockquote>"
            )
            return

        if not mentions:
            await status_msg.edit_text("<blockquote>😶 Koi visible human member nahi mila.</blockquote>")
            return

        # ── Delete loading message ───────────────────────────────────
        await status_msg.delete()

        # ── Send mentions in batches ─────────────────────────────────
        # Pehla batch header ke saath
        first_batch = mentions[:BATCH_SIZE]
        await message.reply_text(
            header + ", ".join(first_batch),
            disable_web_page_preview=True
        )

        # Baaki batches
        for i in range(BATCH_SIZE, len(mentions), BATCH_SIZE):
            batch = mentions[i:i + BATCH_SIZE]
            await asyncio.sleep(DELAY)
            await message.reply_text(
                ", ".join(batch),
                disable_web_page_preview=True
            )

    except Exception:
        try:
            await message.reply_text("<blockquote>❌ /tagall mein error aa gaya.</blockquote>")
        except:
            pass
