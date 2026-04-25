# ==============================================================================
# _thumbnails.py - Fixed Ultra-Premium Glassmorphism Edition
# ==============================================================================

import os
import re
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from Elevenyts import config
from Elevenyts.helpers import Track

def trim_to_width(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    ellipsis = "…"
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis

def square_crop(img: Image.Image) -> Image.Image:
    w, h = img.size
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    return img.crop((left, top, left + min_side, top + min_side))

class Thumbnail:
    def __init__(self):
        try:
            self.brand_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 24)
            self.title_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 60)
            self.artist_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 34)
            self.time_font = ImageFont.truetype("Elevenyts/helpers/Inter-Light.ttf", 24)
            self.ctrl_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 55)
        except OSError:
            self.brand_font = self.title_font = self.artist_font = \
                self.time_font = self.ctrl_font = ImageFont.load_default()

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(output_path, "wb") as f:
                        f.write(await resp.read())
        return output_path

    # --- YE METHOD MISSING THA ---
    async def generate(self, song: Track, size=(1280, 720)) -> str:
        try:
            if not os.path.exists("cache"): os.makedirs("cache")
            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_final.png"
            
            if os.path.exists(output): return output
            
            await self.save_thumb(temp, song.thumbnail)
            
            return await asyncio.get_event_loop().run_in_executor(
                None, self._generate_sync, temp, output, song, size
            )
        except Exception as e:
            print(f"Thumbnail Error: {e}")
            return config.DEFAULT_THUMB

    def _get_dominant_color(self, img):
        small_img = img.resize((1, 1))
        color = small_img.getpixel((0, 0))
        return color[:3]

    def _wrap_title(self, title, font, max_w):
        words = title.split()
        lines, current = [], ""
        for word in words:
            test = (current + " " + word).strip()
            if font.getlength(test) <= max_w:
                current = test
            else:
                if current: lines.append(current)
                current = word
        if current: lines.append(current)
        return lines[:2]

    def _generate_sync(self, temp, output, song, size=(1280, 720)):
        try:
            W, H = size
            with Image.open(temp) as raw:
                raw_rgba = raw.convert("RGBA")
                dom_color = self._get_dominant_color(raw_rgba)
                accent = dom_color if sum(dom_color) > 150 else (180, 100, 255)
                bg = raw.resize((W, H)).filter(ImageFilter.GaussianBlur(15))

            overlay = Image.new("RGBA", (W, H), (10, 10, 15, 140))
            bg = Image.alpha_composite(bg, overlay)

            # --- GLASS BOX ---
            bx1, by1, bx2, by2 = 80, 100, W - 80, H - 100
            
            # Shadow
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow)
            sd.rounded_rectangle([bx1+10, by1+10, bx2+10, by2+10], radius=45, fill=(0, 0, 0, 180))
            bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(20)))

            draw = ImageDraw.Draw(bg)
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=45, fill=(25, 25, 35, 170), outline=(255, 255, 255, 35), width=2)

            # --- ART CIRCLE ---
            circle_r, cx, cy = 215, bx1 + 235, H // 2
            draw.ellipse([cx-circle_r-10, cy-circle_r-10, cx+circle_r+10, cy+circle_r+10], outline=accent, width=5)
            
            with Image.open(temp) as thumb:
                img_t = square_crop(thumb.convert("RGBA")).resize((circle_r*2, circle_r*2), Image.LANCZOS)
                mask = Image.new("L", (circle_r*2, circle_r*2), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, circle_r*2, circle_r*2), fill=255)
                bg.paste(img_t, (cx - circle_r, cy - circle_r), mask)

            # --- TEXT INFO ---
            info_x = cx + circle_r + 65
            info_max_w = bx2 - info_x - 40
            
            draw.text((bx2 - 180, by1 + 35), "Galaxy Bots", font=self.brand_font, fill=(accent[0], accent[1], accent[2], 200))

            title_raw = re.sub(r"\W+", " ", song.title).title()
            lines = self._wrap_title(title_raw, self.title_font, info_max_w)
            ty = by1 + 75
            for i, line in enumerate(lines):
                draw.text((info_x, ty + i*70), line, font=self.title_font, fill=(255, 255, 255))
            
            artist_y = ty + (len(lines) * 75) + 10
            draw.text((info_x, artist_y), f"YouTube | {song.view_count or 'N/A'}", font=self.artist_font, fill=(200, 200, 220))

            # --- PROGRESS BAR ---
            bar_y = artist_y + 85
            bar_x2 = bx2 - 60
            draw.rounded_rectangle([info_x, bar_y, bar_x2, bar_y+8], radius=4, fill=(255, 255, 255, 30))
            
            fill_w = int((bar_x2 - info_x) * 0.42)
            draw.rounded_rectangle([info_x, bar_y, info_x + fill_w, bar_y+8], radius=4, fill=accent)
            draw.ellipse([info_x + fill_w - 10, bar_y - 6, info_x + fill_w + 10, bar_y + 14], fill=accent)

            # --- CONTROLS ---
            ctrl_y = by2 - 95
            mid_x = (info_x + bar_x2) // 2
            
            # Play Circle
            draw.ellipse([mid_x-40, ctrl_y-10, mid_x+40, ctrl_y+70], fill=(accent[0], accent[1], accent[2], 60), outline=accent, width=2)
            draw.text((mid_x-14, ctrl_y+5), "II", font=self.ctrl_font, fill=(255, 255, 255))
            
            draw.text((mid_x-130, ctrl_y+8), "⏮", font=self.ctrl_font, fill=(255, 255, 255, 180))
            draw.text((mid_x+90, ctrl_y+8), "⏭", font=self.ctrl_font, fill=(255, 255, 255, 180))

            bg.convert("RGB").save(output, quality=95)
            if os.path.exists(temp): os.remove(temp)
            return output

        except Exception as e:
            print(f"Sync Error: {e}")
            return config.DEFAULT_THUMB
