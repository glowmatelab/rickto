from pyrogram import filters, types

from Elevenyts import app, db
from Elevenyts.helpers import can_manage_vc


@app.on_message(filters.command(["playmsg"]) & filters.group & ~app.bl_users)
@can_manage_vc
async def _playmsg(_, m: types.Message):
    try:
        await m.delete()
    except Exception:
        pass

    if len(m.command) < 2:
        current = await db.get_playmessage(m.chat.id)
        status = "✅ ON" if current else "❌ OFF"
        return await m.reply_text(
            f"<blockquote>🖼 <b>Play Message:</b> {status}\n\n"
            "• /playmsg on — thumbnail enable karo\n"
            "• /playmsg off — thumbnail disable karo</blockquote>"
        )

    arg = m.command[1].lower()

    if arg == "on":
        await db.set_playmessage(m.chat.id, True)
        await m.reply_text("<blockquote>✅ Play message <b>ON</b> kar diya — ab song bajne pe thumbnail aayega.</blockquote>")
    elif arg == "off":
        await db.set_playmessage(m.chat.id, False)
        await m.reply_text("<blockquote>❌ Play message <b>OFF</b> kar diya — ab thumbnail nahi aayega.</blockquote>")
    else:
        await m.reply_text("<blockquote>❌ Invalid! Use: /playmsg on ya /playmsg off</blockquote>")
