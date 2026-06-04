import asyncio
import random
import re
from pyrogram import filters, types, enums
from Elevenyts import app, config

TRIGGER_PATTERN = re.compile(r"(?i)(\.|@|\/)admin")


async def get_admins(chat_id: int):
    admins = []
    try:
        async for admin in app.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
            user = admin.user
            if user.is_bot or user.is_deleted:
                continue
            if hasattr(admin, 'privileges') and admin.privileges:
                if getattr(admin.privileges, 'is_anonymous', False):
                    continue
            if user.username and user.username.lower() in [u.lower() for u in config.EXCLUDED_USERNAMES]:
                continue
            admins.append(user)
    except Exception:
        pass
    return admins


async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER)
    except Exception:
        return False


# ── @admin / .admin / /admin → Report to 2 random admins ──

@app.on_message(filters.group & filters.regex(r"(?i)(\.|@|\/)admin"))
async def report_to_admins(_, message: types.Message):
    try:
        sender = message.from_user
        if not sender:
            return

        message_text = message.text or message.caption or ""
        cleaned_text = TRIGGER_PATTERN.sub("", message_text).strip()

        reporter = f"@{sender.username}" if sender.username else f"<a href='tg://user?id={sender.id}'>{sender.first_name}</a>"

        admins = await get_admins(message.chat.id)
        if not admins:
            await message.reply_text("<blockquote>❌ Koi admin nahi mila.</blockquote>")
            return

        picked = random.sample(admins, min(2, len(admins)))
        tags = " ".join(
            f"@{u.username}" if u.username else f"<a href='tg://user?id={u.id}'>{u.first_name}</a>"
            for u in picked
        )

        report_text = (
            f"📢 <b>Admin Report</b>\n\n"
            f"👤 <b>Reporter:</b> {reporter}\n"
        )
        if cleaned_text:
            report_text += f"<blockquote>💬 <b>Message:</b> <i>\"{cleaned_text}\"</i></blockquote>\n"
        if message.reply_to_message:
            replied = message.reply_to_message
            replied_user = replied.from_user
            if replied_user:
                replied_mention = f"@{replied_user.username}" if replied_user.username else f"<a href='tg://user?id={replied_user.id}'>{replied_user.first_name}</a>"
                report_text += f"↩️ <b>Reported user:</b> {replied_mention}\n"
            replied_text = replied.text or replied.caption or ""
            if replied_text:
                report_text += f"📝 <b>Their message:</b> <i>\"{replied_text[:200]}\"</i>\n"

        report_text += f"\n🔔 {tags}"

        await message.reply_text(report_text, disable_web_page_preview=True)

    except Exception:
        try:
            await message.reply_text("<blockquote>❌ Report bhejne mein error.</blockquote>")
        except Exception:
            pass


# ── /tagadmins → Sare admins tag karo ──

@app.on_message(filters.group & filters.command("tagadmins"))
async def tag_admins(_, message: types.Message):
    try:
        sender = message.from_user
        if not sender:
            return

        if not await is_admin(message.chat.id, sender.id):
            await message.reply_text("<blockquote>⛔ Sirf admins /tagadmins use kar sakte hain.</blockquote>")
            return

        admins = await get_admins(message.chat.id)
        if not admins:
            await message.reply_text("<blockquote>❌ Koi admin nahi mila.</blockquote>")
            return

        tags = " ".join(
            f"@{u.username}" if u.username else f"<a href='tg://user?id={u.id}'>{u.first_name}</a>"
            for u in admins
        )

        extra = ""
        if message.text and len(message.text.split(None, 1)) > 1:
            extra = f"\n💬 <i>{message.text.split(None, 1)[1].strip()}</i>"

        await message.reply_text(
            f"📢 <b>Admin Tag</b>{extra}\n\n{tags}",
            disable_web_page_preview=True
        )

    except Exception:
        try:
            await message.reply_text("<blockquote>❌ /tagadmins mein error.</blockquote>")
        except Exception:
            pass


# ── /pin → Reply wale message ko permanent pin karo ──

@app.on_message(filters.group & filters.command("pin"))
async def pin_message(_, message: types.Message):
    try:
        sender = message.from_user
        if not sender:
            return

        if not message.reply_to_message:
            await message.reply_text("<blockquote>↩️ Kisi message ko reply karke /pin likho.</blockquote>")
            return

        member = await app.get_chat_member(message.chat.id, sender.id)
        can_pin = False
        if member.status == enums.ChatMemberStatus.OWNER:
            can_pin = True
        elif member.status == enums.ChatMemberStatus.ADMINISTRATOR:
            if member.privileges and getattr(member.privileges, 'can_pin_messages', False):
                can_pin = True

        if not can_pin:
            await message.reply_text("<blockquote>⛔ Tumhare paas pin karne ki permission nahi hai.</blockquote>")
            return

        await app.pin_chat_message(
            message.chat.id,
            message.reply_to_message.id,
            disable_notification=False
        )

        try:
            await message.delete()
        except Exception:
            pass

    except Exception:
        try:
            await message.reply_text("<blockquote>❌ Pin karne mein error. Bot ko pin permission do.</blockquote>")
        except Exception:
            pass
