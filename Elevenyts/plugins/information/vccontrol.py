from pyrogram import filters, enums
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import CreateGroupCall, DiscardGroupCall, GetGroupCall, EditGroupCallParticipant
from pyrogram.raw.types import InputGroupCall
from pyrogram.types import Message
from Elevenyts import app, db
from Elevenyts.helpers._admins import admin_check

@app.on_message(filters.command(["vcstart", "startvc"]) & filters.group)
@admin_check
async def start_vc(_, m: Message):
    chat_id = m.chat.id
    msg = await m.reply("<b>⏳ Voice Chat start ho rahi hai...</b>")
    try:
        assistant = await db.get_client(chat_id)
        if not assistant:
            return await msg.edit_text("<b>❌ Assistant available nahi hai!</b>\nSTRING_SESSION check karo .env mein.")
        peer = await assistant.resolve_peer(chat_id)
        await assistant.invoke(
            CreateGroupCall(
                peer=peer,
                random_id=assistant.rnd_id() // 9000000000,
            )
        )
        await msg.edit_text("<b>🎧 Voice Chat Successfully Start Ho Gayi!</b>")
    except Exception as e:
        err = str(e)
        if "GROUPCALL_ALREADY_STARTED" in err:
            await msg.edit_text("<b>⚠️ Voice Chat pehle se chal rahi hai!</b>")
        else:
            await msg.edit_text(
                f"<b>❌ VC start nahi hui!</b>\n"
                f"<b>Reason:</b> <code>{err}</code>\n\n"
                f"<b>Fix:</b> Assistant ko group mein admin banao aur VC permission do."
            )

@app.on_message(filters.command(["vcend", "endvc"]) & filters.group)
@admin_check
async def end_vc(_, m: Message):
    chat_id = m.chat.id
    msg = await m.reply("<b>⏳ Voice Chat band ho rahi hai...</b>")
    try:
        assistant = await db.get_client(chat_id)
        if not assistant:
            return await msg.edit_text("<b>❌ Assistant available nahi hai!</b>\nSTRING_SESSION check karo .env mein.")
        peer = await assistant.resolve_peer(chat_id)
        full_chat = await assistant.invoke(GetFullChannel(channel=peer))
        group_call = full_chat.full_chat.call
        if not group_call:
            return await msg.edit_text("<b>⚠️ Koi Voice Chat chal nahi rahi!</b>")
        await assistant.invoke(DiscardGroupCall(call=group_call))
        await msg.edit_text("<b>🔇 Voice Chat Successfully Band Ho Gayi!</b>")
    except Exception as e:
        err = str(e)
        if "GROUPCALL_FORBIDDEN" in err:
            await msg.edit_text(
                "<b>❌ Permission nahi hai!</b>\n"
                "Assistant ko <b>VC manage karne ki permission</b> do group mein."
            )
        elif "GROUPCALL_INVALID" in err:
            await msg.edit_text("<b>⚠️ Koi Voice Chat chal nahi rahi!</b>")
        else:
            await msg.edit_text(f"<b>❌ Error:</b> <code>{err}</code>")

@app.on_message(filters.command("vcmembers") & filters.group)
@admin_check
async def vc_members(_, m: Message):
    chat_id = m.chat.id
    msg = await m.reply("<b>⏳ VC members fetch ho rahe hain...</b>")
    try:
        assistant = await db.get_client(chat_id)
        if not assistant:
            return await msg.edit_text("<b>❌ Assistant available nahi hai!</b>")
        peer = await assistant.resolve_peer(chat_id)
        full_chat = await assistant.invoke(GetFullChannel(channel=peer))
        group_call = full_chat.full_chat.call
        if not group_call:
            return await msg.edit_text("<b>⚠️ Koi Voice Chat chal nahi rahi!</b>")
        call_info = await assistant.invoke(
            GetGroupCall(call=InputGroupCall(id=group_call.id, access_hash=group_call.access_hash), limit=100)
        )
        participants = call_info.participants
        if not participants:
            return await msg.edit_text("<b>⚠️ VC mein koi nahi hai!</b>")
        text = f"<b>🎧 VC Members ({len(participants)}):</b>\n\n"
        for i, p in enumerate(participants, 1):
            try:
                user = await assistant.get_users(p.peer.user_id)
                name = user.first_name
                username = f"@{user.username}" if user.username else f"<code>{user.id}</code>"
                muted = "🔇" if p.muted else "🎙️"
                text += f"{i}. {muted} <b>{name}</b> — {username}\n"
            except Exception:
                text += f"{i}. <code>{p.peer}</code>\n"
        await msg.edit_text(text, parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        await msg.edit_text(f"<b>❌ Error:</b> <code>{e}</code>")

@app.on_message(filters.command("vcmute") & filters.group)
@admin_check
async def vc_mute(_, m: Message):
    chat_id = m.chat.id
    target_user = None
    if m.reply_to_message:
        target_user = m.reply_to_message.from_user
    elif len(m.command) > 1:
        try:
            target_user = await app.get_users(m.command[1])
        except Exception:
            return await m.reply("<b>❌ User nahi mila!</b>")
    if not target_user:
        return await m.reply(
            "<b>⚠️ Kisi ko mention karo ya reply karo!</b>\n"
            "<code>/vcmute @username</code>"
        )
    msg = await m.reply("<b>⏳ Mute ho raha hai...</b>")
    try:
        assistant = await db.get_client(chat_id)
        peer = await assistant.resolve_peer(chat_id)
        full_chat = await assistant.invoke(GetFullChannel(channel=peer))
        group_call = full_chat.full_chat.call
        if not group_call:
            return await msg.edit_text("<b>⚠️ Koi VC chal nahi rahi!</b>")
        target_peer = await assistant.resolve_peer(target_user.id)
        await assistant.invoke(
            EditGroupCallParticipant(
                call=InputGroupCall(id=group_call.id, access_hash=group_call.access_hash),
                participant=target_peer,
                muted=True,
            )
        )
        await msg.edit_text(f"<b>🔇 {target_user.first_name} ko VC mein mute kar diya!</b>")
    except Exception as e:
        await msg.edit_text(f"<b>❌ Error:</b> <code>{e}</code>")

@app.on_message(filters.command("vcunmute") & filters.group)
@admin_check
async def vc_unmute(_, m: Message):
    chat_id = m.chat.id
    target_user = None
    if m.reply_to_message:
        target_user = m.reply_to_message.from_user
    elif len(m.command) > 1:
        try:
            target_user = await app.get_users(m.command[1])
        except Exception:
            return await m.reply("<b>❌ User nahi mila!</b>")
    if not target_user:
        return await m.reply(
            "<b>⚠️ Kisi ko mention karo ya reply karo!</b>\n"
            "<code>/vcunmute @username</code>"
        )
    msg = await m.reply("<b>⏳ Unmute ho raha hai...</b>")
    try:
        assistant = await db.get_client(chat_id)
        peer = await assistant.resolve_peer(chat_id)
        full_chat = await assistant.invoke(GetFullChannel(channel=peer))
        group_call = full_chat.full_chat.call
        if not group_call:
            return await msg.edit_text("<b>⚠️ Koi VC chal nahi rahi!</b>")
        target_peer = await assistant.resolve_peer(target_user.id)
        await assistant.invoke(
            EditGroupCallParticipant(
                call=InputGroupCall(id=group_call.id, access_hash=group_call.access_hash),
                participant=target_peer,
                muted=False,
            )
        )
        await msg.edit_text(f"<b>🎙️ {target_user.first_name} ko VC mein unmute kar diya!</b>")
    except Exception as e:
        await msg.edit_text(f"<b>❌ Error:</b> <code>{e}</code>")
