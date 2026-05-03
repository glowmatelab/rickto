# ==============================================================================
# Elevenyts - Professional Apple Music Style Thumbnail Generator
# ==============================================================================

import os
import re
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from Elevenyts import config

# Standard Fonts - Inhe apne path ke hisab se check kar lena
FONT_BOLD = "Elevenyts/helpers/Raleway-Bold.ttf"
FONT_REG = "Elevenyts/helpers/Inter-Light.ttf"

class Thumbnail:
    def __init__(self):
        try:
            self.title_font = ImageFont.truetype(FONT_BOLD, 45)
            self.artist_font = ImageFont.truetype(FONT_REG, 30)
            self.time_font = ImageFont.truetype(FONT_REG, 22)
            self.badge_font = ImageFont.truetype(FONT_BOLD, 18)
            self.icon_font_lg = ImageFont.truetype(FONT_BOLD, 80) # For Play/Pause
            self.icon_font_md = ImageFont.truetype(FONT_BOLD, 50) # For Forward/Rewind
        except OSError:
            self.title_font = self.artist_font = self.time_font = \
                self.badge_font = self.icon_font_lg = self.icon_font_md = ImageFont.load_default()

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(output_path, "wb") as f:
                        f.write(await resp.read())
        return output_path

    async def generate(self, song, size=(1280, 720)) -> str:
        """Main entry point for the bot to call"""
        try:
            # Ensure cache exists
            if not os.path.exists("cache"):
                os.makedirs("cache")

            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_modern.png"

            if os.path.exists(output):
                return output

            # Download thumbnail image
            await self.save_thumb(temp, song.thumbnail)

            # Process image in a separate thread to keep bot responsive
            return await asyncio.get_event_loop().run_in_executor(
                None, self._generate_sync, temp, output, song, size
            )
        except Exception as e:
            print(f"Thumbnail Error: {e}")
            return config.DEFAULT_THUMB

    def _generate_sync(self, temp, output, song, size):
        W, H = size
        try:
            # 1. Background: Deep Blur + Dark Overlay
            with Image.open(temp) as raw:
                bg = raw.convert("RGBA").resize((W, H))
                bg = bg.filter(ImageFilter.GaussianBlur(100))
                overlay = Image.new("RGBA", (W, H), (0, 0, 0, 170)) # Adjusted darkness
                bg = Image.alpha_composite(bg, overlay)

            draw = ImageDraw.Draw(bg)

            # 2. Left Side: Rounded Artwork (Premium Square)
            margin = 100
            thumb_size = H - (margin * 2)
            with Image.open(temp) as raw_art:
                w, h = raw_art.size
                min_s = min(w, h)
                art = raw_art.crop(((w-min_s)//2, (h-min_s)//2, (w+min_s)//2, (h+min_s)//2))
                art = art.convert("RGBA").resize((thumb_size, thumb_size))
                
            mask = Image.new("L", art.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, *art.size), 45, fill=255)
            bg.paste(art, (margin, margin), mask)

            # 3. Right Side Layout Logic
            right_start_x = margin + thumb_size + 85
            right_width = W - right_start_x - 80
            center_x = right_start_x + (right_width // 2)

            # Title & Artist
            clean_title = song.title[:28] + "..." if len(song.title) > 28 else song.title
            draw.text((right_start_x, 130), clean_title, font=self.title_font, fill=(255, 255, 255))
            draw.text((right_start_x, 195), "Antavion • YouTube", font=self.artist_font, fill=(180, 180, 180))

            # 4. Progress Bar
            bar_y = 320
            bar_h = 7
            draw.rounded_rectangle([right_start_x, bar_y, right_start_x + right_width, bar_y + bar_h], radius=4, fill=(255, 255, 255, 50))
            # Progress fill (visual only)
            draw.rounded_rectangle([right_start_x, bar_y, right_start_x + (right_width * 0.38), bar_y + bar_h], radius=4, fill=(255, 255, 255, 220))

            # Floating Badge (Center of bar)
            badge_text = "ANTAVION"
            bw = self.badge_font.getlength(badge_text) + 20
            draw.rounded_rectangle([center_x - (bw/2), bar_y - 12, center_x + (bw/2), bar_y + 18], radius=8, fill=(60, 60, 60, 200))
            draw.text((center_x - (bw/2) + 10, bar_y - 9), badge_text, font=self.badge_font, fill=(255, 255, 255))

            # Timestamps
            draw.text((right_start_x, bar_y + 25), "0:03", font=self.time_font, fill=(160, 160, 160))
            duration = getattr(song, 'duration', '04:20')
            draw.text((right_start_x + right_width - 70, bar_y + 25), f"-{duration}", font=self.time_font, fill=(160, 160, 160))

            # 5. Main Controls (Center Aligned)
            ctrl_y = 440
            # Rewind
            draw.text((center_x - 180, ctrl_y + 12), "◄◄", font=self.icon_font_md, fill=(255, 255, 255))
            # Pause
            draw.text((center_x - 22, ctrl_y), "||", font=self.icon_font_lg, fill=(255, 255, 255))
            # Forward
            draw.text((center_x + 130, ctrl_y + 12), "►►", font=self.icon_font_md, fill=(255, 255, 255))

            # 6. Volume Slider
            vol_y = 590
            vol_bar_w = right_width * 0.75
            vol_x = center_x - (vol_bar_w // 2)
            draw.rounded_rectangle([vol_x, vol_y, vol_x + vol_bar_w, vol_y + 5], radius=3, fill=(255, 255, 255, 50))
            draw.rounded_rectangle([vol_x, vol_y, vol_x + (vol_bar_w * 0.7), vol_y + 5], radius=3, fill=(255, 255, 255, 180))
            # Volume Dot
            vx = vol_x + (vol_bar_w * 0.7)
            draw.ellipse([vx-8, vol_y-6, vx+8, vol_y+10], fill=(255, 255, 255))

            # 7. Bottom Icons
            draw.text((right_start_x + 60, 670), "💬", font=self.artist_font, fill=(255, 255, 255, 180))
            draw.text((right_start_x + right_width - 90, 670), "☰", font=self.artist_font, fill=(255, 255, 255, 180))

            # Save Output
            final = bg.convert("RGB")
            final.save(output, quality=95)
            
            if os.path.exists(temp):
                os.remove(temp)
                
            return output
        except Exception as e:
            print(f"Drawing Error: {e}")
            return config.DEFAULT_THUMB
