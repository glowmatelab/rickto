import os
from pyrogram import filters, types
from Elevenyts import app, db, lang


@app.on_message(filters.command(["ac", "activevc"]) & app.sudo_filter)
@lang.language()
async def _activevc(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    if not db.active_calls:
        return await m.reply_text(m.lang["vc_empty"])

    if m.command[0] == "ac":
        return await m.reply_text(m.lang["vc_count"].format(len(db.active_calls)))

    sent = await m.reply_text(m.lang["vc_fetching"])
    text = ""

    for i, chat in enumerate(db.active_calls):
        try:
            chat_info = await app.get_chat(chat)
            chat_name = chat_info.title or "Unknown"
        except Exception:
            chat_name = "Unknown"

        text += (
            f"\n<blockquote>"
            f"<b>{i+1}. {chat_name}</b>\n"
            f"   🆔 <code>{chat}</code>"
            f"</blockquote>"
        )

    if not text:
        return await sent.edit_text(m.lang["vc_empty"])

    if len(text) < 4000:
        return await sent.edit_text(
            f"<b>🎙 ᴀᴄᴛɪᴠᴇ ꜱᴛʀᴇᴀᴍꜱ — {len(db.active_calls)}</b>\n" + text
        )

    with open("activevc.txt", "w") as f:
        f.write(text)

    try:
        await sent.edit_media(
            media=types.InputMediaDocument(
                media="activevc.txt",
                caption=m.lang["vc_list"],
            )
        )
    finally:
        os.remove("activevc.txt")
