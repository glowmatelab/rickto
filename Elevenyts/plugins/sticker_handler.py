import os
from PIL import Image, ImageFilter
from pyrogram import filters
from Elevenyts import app

# --- STICKER PROCESSING LOGIC ---
async def process_sticker(image_path):
    sticker_path = f"cache/sticker_{os.path.basename(image_path)}.webp"
    try:
        if not os.path.exists("cache"):
            os.makedirs("cache")

        with Image.open(image_path) as img:
            img = img.convert("RGBA")
            # Telegram's 512x512 rule
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
            # Adding White Outline for Pro Look
            alpha = img.getchannel('A')
            outline = alpha.filter(ImageFilter.MaxFilter(5))
            canvas = Image.new("RGBA", img.size, (0, 0, 0, 0))
            white_bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            canvas.paste(white_bg, mask=outline)
            canvas.paste(img, (0, 0), mask=img)
            
            canvas.save(sticker_path, "WEBP")
        return sticker_path
    except Exception as e:
        print(f"Error processing sticker: {e}")
        return None

# --- COMMAND HANDLER ---
@app.on_message(filters.command(["sticker", "makesticker"]) & filters.reply)
async def sticker_cmd(client, message):
    # Check if reply is a photo
    if not message.reply_to_message.photo:
        return await message.reply_text("Bhai, kisi photo par reply karke command do!")

    status = await message.reply_text("🎨 Sticker bana raha hoon...")
    
    # 1. Download image
    img_path = await message.reply_to_message.download()
    
    # 2. Process to sticker
    sticker_file = await process_sticker(img_path)
    
    try:
        if sticker_file:
            # 3. Send & Delete Status
            await message.reply_sticker(sticker_file)
            await status.delete()
        else:
            await status.edit("❌ Error: Sticker nahi ban paya.")
    finally:
        # 4. Cleanup: Sab delete kar do storage bachane ke liye
        if os.path.exists(img_path): os.remove(img_path)
        if sticker_file and os.path.exists(sticker_file): os.remove(sticker_file)
