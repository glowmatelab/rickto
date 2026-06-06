from pyrogram import filters, enums
from pyrogram.types import Message
from pyrogram.errors import ChatAdminRequired, UserAdminInvalid

from Elevenyts import app, lang
from Elevenyts.helpers._admins import admin_check


# ============== BAN ==============

@app.on_message(filters.command("ban") & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def ban_user(_, m: Message):
    try:
        await m.delete()
    except:
        pass

    target = None
    reason = "No reason provided"

    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user
        if len(m.command) > 1:
            reason = " ".join(m.command[1:])
    elif len(m.command) > 1:
        try:
            target = await app.get_users(m.command[1])
            if len(m.command) > 2:
                reason = " ".join(m.command[2:])
        except:
            return await m.reply("<blockquote>❌ User nahi mila!</blockquote>")
    else:
        return await m.reply("<blockquote>ᴜꜱᴀɢᴇ: <code>/ban @user [reason]</code>\nya kisi message pe reply karo</blockquote>")

    if target.id in app.sudoers:
        return await m.reply("<blockquote>❌ Sudo user ko ban nahi kar sakte!</blockquote>")

    try:
        await app.ban_chat_member(m.chat.id, target.id)
        await m.reply(
            f"<blockquote><u><b>🚫 ᴜꜱᴇʀ ʙᴀɴɴᴇᴅ</b></u>\n\n"
            f"<b>ᴜꜱᴇʀ:</b> {target.mention}\n"
            f"<b>ɪᴅ:</b> <code>{target.id}</code>\n"
            f"<b>ʀᴇᴀꜱᴏɴ:</b> {reason}</blockquote>"
        )
    except ChatAdminRequired:
        await m.reply("<blockquote>❌ Bot ko admin banana pado ban karne ke liye!</blockquote>")
    except UserAdminInvalid:
        await m.reply("<blockquote>❌ Is admin ko ban nahi kar sakte!</blockquote>")
    except Exception as e:
        await m.reply(f"<blockquote>❌ Error: <code>{e}</code></blockquote>")


# ============== UNBAN ==============

@app.on_message(filters.command("unban") & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def unban_user(_, m: Message):
    try:
        await m.delete()
    except:
        pass

    target = None

    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user
    elif len(m.command) > 1:
        try:
            target = await app.get_users(m.command[1])
        except:
            return await m.reply("<blockquote>❌ User nahi mila!</blockquote>")
    else:
        return await m.reply("<blockquote>ᴜꜱᴀɢᴇ: <code>/unban @user</code>\nya kisi message pe reply karo</blockquote>")

    try:
        await app.unban_chat_member(m.chat.id, target.id)
        await m.reply(
            f"<blockquote><u><b>✅ ᴜꜱᴇʀ ᴜɴʙᴀɴɴᴇᴅ</b></u>\n\n"
            f"<b>ᴜꜱᴇʀ:</b> {target.mention}\n"
            f"<b>ɪᴅ:</b> <code>{target.id}</code></blockquote>"
        )
    except ChatAdminRequired:
        await m.reply("<blockquote>❌ Bot ko admin banana pado!</blockquote>")
    except Exception as e:
        await m.reply(f"<blockquote>❌ Error: <code>{e}</code></blockquote>")


# ============== KICK ==============

@app.on_message(filters.command("kick") & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def kick_user(_, m: Message):
    try:
        await m.delete()
    except:
        pass

    target = None
    reason = "No reason provided"

    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user
        if len(m.command) > 1:
            reason = " ".join(m.command[1:])
    elif len(m.command) > 1:
        try:
            target = await app.get_users(m.command[1])
            if len(m.command) > 2:
                reason = " ".join(m.command[2:])
        except:
            return await m.reply("<blockquote>❌ User nahi mila!</blockquote>")
    else:
        return await m.reply("<blockquote>ᴜꜱᴀɢᴇ: <code>/kick @user [reason]</code>\nya kisi message pe reply karo</blockquote>")

    if target.id in app.sudoers:
        return await m.reply("<blockquote>❌ Sudo user ko kick nahi kar sakte!</blockquote>")

    try:
        await app.ban_chat_member(m.chat.id, target.id)
        await app.unban_chat_member(m.chat.id, target.id)  # Kick = ban + turant unban
        await m.reply(
            f"<blockquote><u><b>👢 ᴜꜱᴇʀ ᴋɪᴄᴋᴇᴅ</b></u>\n\n"
            f"<b>ᴜꜱᴇʀ:</b> {target.mention}\n"
            f"<b>ɪᴅ:</b> <code>{target.id}</code>\n"
            f"<b>ʀᴇᴀꜱᴏɴ:</b> {reason}</blockquote>"
        )
    except ChatAdminRequired:
        await m.reply("<blockquote>❌ Bot ko admin banana pado!</blockquote>")
    except UserAdminInvalid:
        await m.reply("<blockquote>❌ Is admin ko kick nahi kar sakte!</blockquote>")
    except Exception as e:
        await m.reply(f"<blockquote>❌ Error: <code>{e}</code></blockquote>")


# ============== MUTE ==============

@app.on_message(filters.command("mute") & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def mute_user(_, m: Message):
    try:
        await m.delete()
    except:
        pass

    target = None
    reason = "No reason provided"

    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user
        if len(m.command) > 1:
            reason = " ".join(m.command[1:])
    elif len(m.command) > 1:
        try:
            target = await app.get_users(m.command[1])
            if len(m.command) > 2:
                reason = " ".join(m.command[2:])
        except:
            return await m.reply("<blockquote>❌ User nahi mila!</blockquote>")
    else:
        return await m.reply("<blockquote>ᴜꜱᴀɢᴇ: <code>/mute @user [reason]</code>\nya kisi message pe reply karo</blockquote>")

    if target.id in app.sudoers:
        return await m.reply("<blockquote>❌ Sudo user ko mute nahi kar sakte!</blockquote>")

    try:
        await app.restrict_chat_member(
            m.chat.id,
            target.id,
            enums.ChatPermissions()  # Sabhi permissions remove = mute
        )
        await m.reply(
            f"<blockquote><u><b>🔇 ᴜꜱᴇʀ ᴍᴜᴛᴇᴅ</b></u>\n\n"
            f"<b>ᴜꜱᴇʀ:</b> {target.mention}\n"
            f"<b>ɪᴅ:</b> <code>{target.id}</code>\n"
            f"<b>ʀᴇᴀꜱᴏɴ:</b> {reason}</blockquote>"
        )
    except ChatAdminRequired:
        await m.reply("<blockquote>❌ Bot ko admin banana pado!</blockquote>")
    except UserAdminInvalid:
        await m.reply("<blockquote>❌ Is admin ko mute nahi kar sakte!</blockquote>")
    except Exception as e:
        await m.reply(f"<blockquote>❌ Error: <code>{e}</code></blockquote>")


# ============== UNMUTE ==============

@app.on_message(filters.command("unmute") & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def unmute_user(_, m: Message):
    try:
        await m.delete()
    except:
        pass

    target = None

    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user
    elif len(m.command) > 1:
        try:
            target = await app.get_users(m.command[1])
        except:
            return await m.reply("<blockquote>❌ User nahi mila!</blockquote>")
    else:
        return await m.reply("<blockquote>ᴜꜱᴀɢᴇ: <code>/unmute @user</code>\nya kisi message pe reply karo</blockquote>")

    try:
        await app.restrict_chat_member(
            m.chat.id,
            target.id,
            enums.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
        )
        await m.reply(
            f"<blockquote><u><b>🔊 ᴜꜱᴇʀ ᴜɴᴍᴜᴛᴇᴅ</b></u>\n\n"
            f"<b>ᴜꜱᴇʀ:</b> {target.mention}\n"
            f"<b>ɪᴅ:</b> <code>{target.id}</code></blockquote>"
        )
    except ChatAdminRequired:
        await m.reply("<blockquote>❌ Bot ko admin banana pado!</blockquote>")
    except Exception as e:
        await m.reply(f"<blockquote>❌ Error: <code>{e}</code></blockquote>")


# ============== PROMOTE ==============

@app.on_message(filters.command("promote") & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def promote_user(_, m: Message):
    try:
        await m.delete()
    except:
        pass

    target = None
    title = ""

    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user
        if len(m.command) > 1:
            title = " ".join(m.command[1:])
    elif len(m.command) > 1:
        try:
            target = await app.get_users(m.command[1])
            if len(m.command) > 2:
                title = " ".join(m.command[2:])
        except:
            return await m.reply("<blockquote>❌ User nahi mila!</blockquote>")
    else:
        return await m.reply("<blockquote>ᴜꜱᴀɢᴇ: <code>/promote @user [title]</code>\nya kisi message pe reply karo</blockquote>")

    try:
        await app.promote_chat_member(
            m.chat.id,
            target.id,
            privileges=enums.ChatPrivileges(
                can_manage_chat=True,
                can_delete_messages=True,
                can_restrict_members=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_manage_video_chats=True,
            )
        )
        if title:
            try:
                await app.set_administrator_title(m.chat.id, target.id, title)
            except:
                pass

        await m.reply(
            f"<blockquote><u><b>⭐ ᴜꜱᴇʀ ᴘʀᴏᴍᴏᴛᴇᴅ</b></u>\n\n"
            f"<b>ᴜꜱᴇʀ:</b> {target.mention}\n"
            f"<b>ɪᴅ:</b> <code>{target.id}</code>"
            + (f"\n<b>ᴛɪᴛʟᴇ:</b> {title}" if title else "")
            + "</blockquote>"
        )
    except ChatAdminRequired:
        await m.reply("<blockquote>❌ Bot ko promote karne ki permission nahi!</blockquote>")
    except Exception as e:
        await m.reply(f"<blockquote>❌ Error: <code>{e}</code></blockquote>")


# ============== DEMOTE ==============

@app.on_message(filters.command("demote") & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def demote_user(_, m: Message):
    try:
        await m.delete()
    except:
        pass

    target = None

    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user
    elif len(m.command) > 1:
        try:
            target = await app.get_users(m.command[1])
        except:
            return await m.reply("<blockquote>❌ User nahi mila!</blockquote>")
    else:
        return await m.reply("<blockquote>ᴜꜱᴀɢᴇ: <code>/demote @user</code>\nYa kisi message pe reply karo</blockquote>")

    try:
        await app.promote_chat_member(
            m.chat.id,
            target.id,
            privileges=enums.ChatPrivileges()  # Sabhi privileges remove
        )
        await m.reply(
            f"<blockquote><u><b>🔽 ᴜꜱᴇʀ ᴅᴇᴍᴏᴛᴇᴅ</b></u>\n\n"
            f"<b>ᴜꜱᴇʀ:</b> {target.mention}\n"
            f"<b>ɪᴅ:</b> <code>{target.id}</code></blockquote>"
        )
    except ChatAdminRequired:
        await m.reply("<blockquote>❌ Bot ko demote karne ki permission nahi!</blockquote>")
    except UserAdminInvalid:
        await m.reply("<blockquote>❌ Is user ko demote nahi kar sakte!</blockquote>")
    except Exception as e:
        await m.reply(f"<blockquote>❌ Error: <code>{e}</code></blockquote>")


# ============== WARN ==============

warn_db = {}  # Simple in-memory warn store (MongoDB ke liye db mein add kar sakte ho)
WARN_LIMIT = 3


@app.on_message(filters.command("warn") & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def warn_user(_, m: Message):
    try:
        await m.delete()
    except:
        pass

    target = None
    reason = "No reason provided"

    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user
        if len(m.command) > 1:
            reason = " ".join(m.command[1:])
    elif len(m.command) > 1:
        try:
            target = await app.get_users(m.command[1])
            if len(m.command) > 2:
                reason = " ".join(m.command[2:])
        except:
            return await m.reply("<blockquote>❌ User nahi mila!</blockquote>")
    else:
        return await m.reply("<blockquote>ᴜꜱᴀɢᴇ: <code>/warn @user [reason]</code>\nya kisi message pe reply karo</blockquote>")

    if target.id in app.sudoers:
        return await m.reply("<blockquote>❌ Sudo user ko warn nahi kar sakte!</blockquote>")

    key = (m.chat.id, target.id)
    warn_db[key] = warn_db.get(key, 0) + 1
    count = warn_db[key]

    if count >= WARN_LIMIT:
        try:
            await app.ban_chat_member(m.chat.id, target.id)
            warn_db[key] = 0
            return await m.reply(
                f"<blockquote><u><b>🚫 ᴡᴀʀɴ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ — ʙᴀɴɴᴇᴅ!</b></u>\n\n"
                f"<b>ᴜꜱᴇʀ:</b> {target.mention}\n"
                f"<b>{WARN_LIMIT}/{WARN_LIMIT} warns</b> ke baad ban ho gaya!</blockquote>"
            )
        except Exception as e:
            return await m.reply(f"<blockquote>❌ Ban nahi hua: <code>{e}</code></blockquote>")

    await m.reply(
        f"<blockquote><u><b>⚠️ ᴜꜱᴇʀ ᴡᴀʀɴᴇᴅ</b></u>\n\n"
        f"<b>ᴜꜱᴇʀ:</b> {target.mention}\n"
        f"<b>ᴡᴀʀɴꜱ:</b> {count}/{WARN_LIMIT}\n"
        f"<b>ʀᴇᴀꜱᴏɴ:</b> {reason}</blockquote>"
    )


@app.on_message(filters.command("resetwarn") & filters.group & ~app.bl_users)
@lang.language()
@admin_check
async def reset_warn(_, m: Message):
    try:
        await m.delete()
    except:
        pass

    target = None

    if m.reply_to_message and m.reply_to_message.from_user:
        target = m.reply_to_message.from_user
    elif len(m.command) > 1:
        try:
            target = await app.get_users(m.command[1])
        except:
            return await m.reply("<blockquote>❌ User nahi mila!</blockquote>")
    else:
        return await m.reply("<blockquote>ᴜꜱᴀɢᴇ: <code>/resetwarn @user</code></blockquote>")

    key = (m.chat.id, target.id)
    warn_db[key] = 0
    await m.reply(
        f"<blockquote><u><b>✅ ᴡᴀʀɴꜱ ʀᴇꜱᴇᴛ</b></u>\n\n"
        f"<b>ᴜꜱᴇʀ:</b> {target.mention} ke sabhi warns clear ho gaye!</blockquote>"
    )
