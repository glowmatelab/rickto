import random
from pyrogram import filters
from Elevenyts import app

# Mapping for dice commands
DICE_MAP = {
    "dice": "🎲",
    "jackpot": "🎰",
    "dart": "🎯",
    "basket": "🏀",
    "ball": "🎳",
    "football": "⚽"
}

# 1. Universal Dice/Games Handler
@app.on_message(filters.command(list(DICE_MAP.keys())))
async def universal_dice_handler(bot, message):
    cmd = message.command[0]
    emoji = DICE_MAP.get(cmd)
    
    try:
        try:
            await message.delete()
        except:
            pass

        x = await bot.send_dice(message.chat.id, emoji)
        score = x.dice.value
        
        # Special logic for Jackpot
        if cmd == "jackpot":
            # 64 is the winning value for 777 in Telegram
            result = "WINNER! 🤑" if score == 64 else "Try again! ✨"
            await message.reply_text(f"🎰 {message.from_user.mention} spun: **{score}**\nResult: {result}", quote=True)
        else:
            await message.reply_text(f"{emoji} {message.from_user.mention} scored: **{score}**", quote=True)

    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

# 2. Emoji Handler (Direct emoji sending)
@app.on_message(filters.dice)
async def dice_emoji_handler(bot, message):
    try:
        score = message.dice.value
        emoji = message.dice.emoji
        await message.reply_text(f"{emoji} {message.from_user.mention} scored: **{score}**", quote=True)
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

# 3. Shout Feature (Text Stylizer)
@app.on_message(filters.command("shout"))
async def shout_handler(bot, message):
    if len(message.command) < 2:
        return await message.reply_text("Bhai, kuch likho toh sahi! Example: `/shout hello`")
    
    text = message.text.split(None, 1)[1]
    # Spacing out characters and making them UPPERCASE
    shouted_text = " ".join(list(text.upper()))
    
    response = (
        f"📢 **STREET SHOUT!**\n"
        f"━━━━━━━━━━━━━━\n"
        f"✨ `{shouted_text}`\n"
        f"━━━━━━━━━━━━━━"
    )
    await message.reply_text(response)
