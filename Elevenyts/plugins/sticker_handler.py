# Elevenyts/plugins/features/sticker.py

import os
from PIL import Image, ImageFilter
from pyrogram import filters, enums
from pyrogram.types import Message
from Elevenyts import app


async def process_sticker(image_path: str) -> str | None:
    os.makedirs("cache", exist_ok=True)
    sticker_path = f"cache/sticker_{os.path.basename(image_path)}.webp"
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGBA")
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)

            alpha = img.getchannel("A")
            outline = alpha.filter(ImageFilter.MaxFilter(5))
            canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            canvas.paste(white_bg, mask=outline)
            canvas.paste(img, (0, 0), mask=img)
            canvas.save(sticker_path, "WEBP")
        return sticker_path
    except Exception as e:
        print(f"sticker error: {e}")
        return None


@app.on_message(
    filters.command(["sticker", "makesticker"])
    & (filters.group | filters.private)
)
async def sticker_cmd(_, message: Message):
    reply = message.reply_to_message

    # ── reply check ──
    if not reply or not reply.photo:
        await message.reply_text(
            "<blockquote>"
            "⚠️  ɪᴍᴀɢᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ\n\n"
            "ʜᴏᴡ ᴛᴏ ᴜꜱᴇ :\n"
            "  ➊  ꜱᴇɴᴅ ᴀɴʏ ɪᴍᴀɢᴇ\n"
            "  ➋  ʀᴇᴘʟʏ ᴛᴏ ɪᴛ ᴡɪᴛʜ  /sticker"
            "</blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
        return

    status = await message.reply_text(
        "<blockquote>🎨  ᴄʀᴇᴀᴛɪɴɢ ꜱᴛɪᴄᴋᴇʀ...</blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )

    img_path = None
    sticker_path = None
    try:
        img_path = await reply.download()
        sticker_path = await process_sticker(img_path)

        if sticker_path:
            await message.reply_sticker(sticker_path)
            await status.delete()
        else:
            await status.edit_text(
                "<blockquote>❌  ꜱᴛɪᴄᴋᴇʀ ᴄᴏɴᴠᴇʀꜱɪᴏɴ ꜰᴀɪʟᴇᴅ.</blockquote>",
                parse_mode=enums.ParseMode.HTML,
            )
    except Exception as e:
        await status.edit_text(
            f"<blockquote>❌  ᴇʀʀᴏʀ\n\n<code>{e}</code></blockquote>",
            parse_mode=enums.ParseMode.HTML,
        )
    finally:
        if img_path and os.path.exists(img_path):
            os.remove(img_path)
        if sticker_path and os.path.exists(sticker_path):
            os.remove(sticker_path)
