# ==============================================================================
# _thumbnails.py - 3D Circle Layout Premium (THE REAL MAZZA EDITION)
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
            self.brand_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 26)
            self.title_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 62)
            self.title_font_sm = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 50)
            self.artist_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 34)
            self.time_font = ImageFont.truetype("Elevenyts/helpers/Inter-Light.ttf", 26)
            self.ctrl_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 48)
        except OSError:
            self.brand_font = self.title_font = self.title_font_sm = \
                self.artist_font = self.time_font = self.ctrl_font = ImageFont.load_default()

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(output_path, "wb") as f:
                        f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        try:
            if not os.path.exists("cache"): os.makedirs("cache")
            temp, output = f"cache/temp_{song.id}.jpg", f"cache/{song.id}_3d.png"
            if os.path.exists(output): return output
            await self.save_thumb(temp, song.thumbnail)
            return await asyncio.get_event_loop().run_in_executor(None, self._generate_sync, temp, output, song, size)
        except Exception as e:
            print(f"Error: {e}")
            return config.DEFAULT_THUMB

    def _draw_progress_bar(self, draw, x1, y, x2, fill_ratio=0.45):
        bar_h = 8
        fill_w = int((x2 - x1) * fill_ratio)
        draw.rounded_rectangle([x1, y, x2, y + bar_h], radius=5, fill=(255, 255, 255, 30))
        draw.rounded_rectangle([x1, y, x1 + fill_w, y + bar_h], radius=5, fill=(180, 100, 255))
        dot_x, dot_y = x1 + fill_w, y + bar_h // 2
        draw.ellipse([dot_x - 12, dot_y - 12, dot_x + 12, dot_y + 12], fill=(220, 160, 255))

    def _wrap_title(self, title, font, max_w):
        words = title.split()
        lines, current = [], ""
        for word in words:
            test = (current + " " + word).strip()
            if font.getlength(test) <= max_w: current = test
            else:
                if current: lines.append(current)
                current = word
        if current: lines.append(current)
        return lines[:2]

    def _generate_sync(self, temp, output, song, size=(1280, 720)):
        try:
            W, H = size
            with Image.open(temp) as raw:
                bg = raw.resize((W, H)).convert("RGBA").filter(ImageFilter.GaussianBlur(12))

            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 110))
            bg = Image.alpha_composite(bg, overlay)

            # --- 3D FLOATING BOX WITH DEEP SHADOW ---
            bx1, by1, bx2, by2 = 100, 120, W - 100, H - 120
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow)
            # Extra deep shadow layers
            sd.rounded_rectangle([bx1+12, by1+12, bx2+12, by2+12], radius=40, fill=(0, 0, 0, 140))
            sd.rounded_rectangle([bx1+20, by1+20, bx2+20, by2+20], radius=40, fill=(0, 0, 0, 90))
            bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(25)))

            draw = ImageDraw.Draw(bg)
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=40, fill=(18, 18, 24, 190), outline=(255, 255, 255, 35), width=2)

            # --- CIRCLE THUMBNAIL ---
            circle_r, cx, cy = 210, bx1 + 220, H // 2
            draw.ellipse([cx-circle_r-10, cy-circle_r-10, cx+circle_r+10, cy+circle_r+10], outline=(180, 100, 255), width=6)
            
            with Image.open(temp) as raw_thumb:
                img_t = square_crop(raw_thumb.convert("RGBA")).resize((circle_r*2, circle_r*2), Image.LANCZOS)
                mask = Image.new("L", (circle_r*2, circle_r*2), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, circle_r*2, circle_r*2), fill=255)
                bg.paste(img_t, (cx - circle_r, cy - circle_r), mask)

            # --- INFO SECTION ---
            info_x = cx + circle_r + 65
            info_max_w = bx2 - info_x - 50
            draw.text((bx2 - 190, by1 + 35), "Galaxy Bots", font=self.brand_font, fill=(180, 120, 255))

            title_raw = re.sub(r"\W+", " ", song.title).title()
            lines = self._wrap_title(title_raw, self.title_font_sm, info_max_w)
            ty = by1 + 80
            for i, line in enumerate(lines):
                draw.text((info_x, ty + i*65), line, font=self.title_font_sm, fill=(255, 255, 255))
            
            artist_y = ty + (len(lines) * 70) + 5
            draw.text((info_x, artist_y), f"YouTube | {song.view_count or 'Unknown'}", font=self.artist_font, fill=(180, 160, 220))

            # Progress Bar
            bar_y = artist_y + 80
            self._draw_progress_bar(draw, info_x, bar_y, bx2 - 60)

            # Time
            duration = getattr(song, 'duration', '0:00')
            draw.text((info_x, bar_y + 25), "01:05", font=self.time_font, fill=(150, 130, 200))
            draw.text((bx2 - 60 - self.time_font.getlength(duration), bar_y + 25), duration, font=self.time_font, fill=(150, 130, 200))

            # --- CONTROLS: THE "MAZZA" PART ---
            ctrl_cy = by2 - 85
            ctrl_cx = (info_x + bx2 - 60) // 2
            
            # Big Glowy Play Circle
            draw.ellipse([ctrl_cx-48, ctrl_cy-48, ctrl_cx+48, ctrl_cy+48], fill=(160, 80, 255, 100), outline=(180, 100, 255), width=3)
            
            # Draw Play Triangle (Centered correctly)
            draw.polygon([(ctrl_cx-12, ctrl_cy-18), (ctrl_cx-12, ctrl_cy+18), (ctrl_cx+18, ctrl_cy)], fill=(255, 255, 255))
            
            # Skip Buttons (⏮ and ⏭)
            draw.text((ctrl_cx - 155, ctrl_cy - 25), "⏮", font=self.ctrl_font, fill=(200, 180, 255))
            draw.text((ctrl_cx + 105, ctrl_cy - 25), "⏭", font=self.ctrl_font, fill=(200, 180, 255))

            # Finalize
            bg.convert("RGB").save(output, quality=95)
            if os.path.exists(temp): os.remove(temp)
            return output

        except Exception as e:
            print(f"Error: {e}")
            return config.DEFAULT_THUMB
