import asyncio
import re
from pyrogram import filters, types, enums
from Elevenyts import app, config

# Pattern to detect admin triggers
TRIGGER_PATTERN = re.compile(r"(?i)(\.|@|\/)admin")

# ─────────────────────────────────────────────
#  Global stop flags  { chat_id: asyncio.Event }
# ─────────────────────────────────────────────
stop_flags: dict[int, asyncio.Event] = {}


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
#  Helper – admin check
# ─────────────────────────────────────────────
async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in (
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        )
    except Exception:
        return False


# ─────────────────────────────────────────────
#  TAG ALL MEMBERS  →  /tagall
# ─────────────────────────────────────────────
BATCH_SIZE = 5      # kitne mentions ek message mein
DELAY      = 1.5    # seconds between batches


@app.on_message(filters.group & filters.command("tagall"))
async def tag_all_members(_, message: types.Message):
    """
    /tagall  – group ke saare human members ko mention karta hai
    Sirf admins use kar sakte hain.
    """
    try:
        sender = message.from_user
        if not sender:
            await message.reply_text("<blockquote>❌ Anonymous admins ye command use nahi kar sakte.</blockquote>")
            return

        if not await is_admin(message.chat.id, sender.id):
            await message.reply_text("<blockquote>⛔ Sirf admins /tagall use kar sakte hain.</blockquote>")
            return

        chat_id = message.chat.id

        # Agar pehle se chal raha hai to rok do
        if chat_id in stop_flags and not stop_flags[chat_id].is_set():
            await message.reply_text("<blockquote>⚠️ Tag already chal raha hai. Pehle /stoptag karo.</blockquote>")
            return

        # Naya stop flag banao (set = stopped, not set = running)
        stop_flags[chat_id] = asyncio.Event()

        # ── Optional custom message ──────────────────────────────────
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
            async for mem in app.get_chat_members(chat_id):
                user = mem.user
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
            stop_flags.pop(chat_id, None)
            return

        if not mentions:
            await status_msg.edit_text("<blockquote>😶 Koi visible human member nahi mila.</blockquote>")
            stop_flags.pop(chat_id, None)
            return

        await status_msg.delete()

        # ── Send in batches, check stop flag every batch ─────────────
        first        = True
        stopped_early = False
        tagged_count  = 0

        for i in range(0, len(mentions), BATCH_SIZE):

            # Stop flag check karo batch se pehle
            if stop_flags.get(chat_id) and stop_flags[chat_id].is_set():
                stopped_early = True
                break

            batch = mentions[i : i + BATCH_SIZE]
            text  = (header + ", ".join(batch)) if first else ", ".join(batch)
            first = False

            await message.reply_text(text, disable_web_page_preview=True)
            tagged_count += len(batch)

            # Delay ke dauran bhi 0.3s–0.3s stop check karo
            for _ in range(int(DELAY / 0.3)):
                if stop_flags.get(chat_id) and stop_flags[chat_id].is_set():
                    stopped_early = True
                    break
                await asyncio.sleep(0.3)

            if stopped_early:
                break

        # ── Done / Stopped summary ───────────────────────────────────
        if stopped_early:
            await message.reply_text(
                f"<blockquote>🛑 <b>Tagging rok di gayi!</b>\n"
                f"Tagged: <b>{tagged_count}</b> / <b>{len(mentions)}</b> members.</blockquote>",
                disable_web_page_preview=True
            )
        else:
            await message.reply_text(
                f"<blockquote>✅ <b>Sabko tag kar diya!</b>\n"
                f"Total: <b>{len(mentions)}</b> members.</blockquote>",
                disable_web_page_preview=True
            )

        stop_flags.pop(chat_id, None)

    except Exception:
        stop_flags.pop(message.chat.id, None)
        try:
            await message.reply_text("<blockquote>❌ /tagall mein error aa gaya.</blockquote>")
        except:
            pass


# ─────────────────────────────────────────────
#  STOP TAG  →  /stoptag
# ─────────────────────────────────────────────
@app.on_message(filters.group & filters.command("stoptag"))
async def stop_tag(_, message: types.Message):
    """
    /stoptag  – chal rahi tagging ko beech mein rok deta hai
    Sirf admins use kar sakte hain.
    """
    try:
        sender = message.from_user
        if not sender:
            await message.reply_text("<blockquote>❌ Anonymous admins ye command use nahi kar sakte.</blockquote>")
            return

        if not await is_admin(message.chat.id, sender.id):
            await message.reply_text("<blockquote>⛔ Sirf admins /stoptag use kar sakte hain.</blockquote>")
            return

        chat_id = message.chat.id

        if chat_id not in stop_flags or stop_flags[chat_id].is_set():
            await message.reply_text("<blockquote>ℹ️ Abhi koi tagging chal nahi rahi.</blockquote>")
            return

        # Flag set karo → tagall loop next check pe rukega
        stop_flags[chat_id].set()
        await message.reply_text(
            "<blockquote>🛑 Tagging band karne ka signal bhej diya…\nAgla batch complete hone ke baad rukegi.</blockquote>"
        )

    except Exception:
        try:
            await message.reply_text("<blockquote>❌ /stoptag mein error aa gaya.</blockquote>")
        except:
            pass
