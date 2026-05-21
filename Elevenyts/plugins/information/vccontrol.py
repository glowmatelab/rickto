from pyrogram import filters
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.phone import CreateGroupCall, DiscardGroupCall
from pyrogram.types import Message

from Elevenyts import app, db
from Elevenyts.helpers._admins import admin_check


@app.on_message(filters.command(["vcstart", "startvc"]) & filters.group)
@admin_check
async def start_vc(_, m: Message):
    chat_id = m.chat.id
    msg = await m.reply("<b>⏳ Voice Chat start ho rahi hai...</b>")

    try:
        assistant = await db.get_assistant(chat_id)
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
        assistant = await db.get_assistant(chat_id)
        peer = await assistant.resolve_peer(chat_id)

        # Pehle current group call fetch karo
        full_chat = await assistant.invoke(
            GetFullChannel(channel=peer)
        )

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
