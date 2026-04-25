# ==============================================================================
# _thumbnails.py - Circle Layout Premium Thumbnail (FIXED)
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
            self.time_font = ImageFont.truetype("Elevenyts/helpers/Inter-Light.ttf", 28)
            self.small_font = ImageFont.truetype("Elevenyts/helpers/Inter-Light.ttf", 22)
            self.ctrl_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 44)
        except OSError:
            self.brand_font = self.title_font = self.title_font_sm = \
                self.artist_font = self.time_font = self.small_font = \
                self.ctrl_font = ImageFont.load_default()

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(output_path, "wb") as f:
                        f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        try:
            if not os.path.exists("cache"):
                os.makedirs("cache")
            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_modern.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)

            return await asyncio.get_event_loop().run_in_executor(
                None, self._generate_sync, temp, output, song, size
            )
        except Exception:
            return config.DEFAULT_THUMB

    def _paste_circle(self, bg, img, center, radius):
        size = radius * 2
        img_resized = img.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        x = center[0] - radius
        y = center[1] - radius
        bg.paste(img_resized, (x, y), mask)

    def _draw_progress_bar(self, draw, x1, y, x2, fill_ratio=0.38):
        bar_h = 7
        actual_w = x2 - x1
        fill_w = int(actual_w * fill_ratio)

        # Track (Background)
        draw.rounded_rectangle([x1, y, x2, y + bar_h], radius=4, fill=(255, 255, 255, 40))
        # Fill (Main Color)
        draw.rounded_rectangle([x1, y, x1 + fill_w, y + bar_h], radius=4, fill=(180, 100, 255))
        
        # Glow Dot
        dot_x, dot_y = x1 + fill_w, y + bar_h // 2
        draw.ellipse([dot_x - 10, dot_y - 10, dot_x + 10, dot_y + 10], fill=(200, 140, 255))

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
                bg = raw.resize((W, H)).convert("RGBA")

            bg = bg.filter(ImageFilter.GaussianBlur(28))
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 130))
            bg = Image.alpha_composite(bg, overlay)

            # Vignette
            vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vd = ImageDraw.Draw(vig)
            for i in range(120):
                alpha = int(200 * (i / 120))
                vd.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, alpha))
            bg = Image.alpha_composite(bg, vig)

            draw = ImageDraw.Draw(bg)
            circle_r, circle_cx, circle_cy = 240, 320, H // 2

            # Glow & Border
            for i in range(20, 0, -5):
                draw.ellipse([circle_cx-circle_r-i, circle_cy-circle_r-i, circle_cx+circle_r+i, circle_cy+circle_r+i], outline=(160, 80, 255, int(60*(i/20))), width=2)
            
            draw.ellipse([circle_cx-circle_r-12, circle_cy-circle_r-12, circle_cx+circle_r+12, circle_cy+circle_r+12], outline=(140, 60, 240), width=10)

            with Image.open(temp) as raw_thumb:
                cropped = square_crop(raw_thumb.convert("RGBA"))
                self._paste_circle(bg, cropped, (circle_cx, circle_cy), circle_r)

            # ─────────────────────────────────────────
            # RIGHT SIDE INFO - LAYOUT FIX
            # ─────────────────────────────────────────
            info_x = circle_cx + circle_r + 70
            bar_x2 = W - 80  # Bound to stay inside the box
            info_max_w = bar_x2 - info_x

            # Brand
            brand_w = self.brand_font.getlength("Galaxy Bots")
            draw.text((W - brand_w - 50, 36), "Galaxy Bots", font=self.brand_font, fill=(160, 100, 230))

            # Title Wrap
            title_raw = re.sub(r"\W+", " ", song.title).title()
            lines = self._wrap_title(title_raw, self.title_font_sm, info_max_w)
            title_y = H // 2 - 180
            for i, line in enumerate(lines):
                draw.text((info_x, title_y + i*60), line, font=self.title_font_sm, fill=(255, 255, 255))
            
            # Artist & Views
            artist_y = title_y + (len(lines) * 65)
            requested_by = getattr(song, 'requested_by', None)
            artist_name = getattr(requested_by, 'first_name', 'YouTube') if requested_by else "YouTube"
            views = song.view_count or "Unknown"
            draw.text((info_x, artist_y), f"{artist_name}  |  {views}", font=self.artist_font, fill=(210, 185, 245))

            # Progress Bar (Fixed Width)
            bar_y = artist_y + 80
            self._draw_progress_bar(draw, info_x, bar_y, bar_x2)

            # Time Labels
            time_y = bar_y + 25
            duration = getattr(song, 'duration', '0:00')
            draw.text((info_x, time_y), "00:00", font=self.time_font, fill=(200, 180, 235))
            dur_w = self.time_font.getlength(duration)
            draw.text((bar_x2 - dur_w, time_y), duration, font=self.time_font, fill=(200, 180, 235))

            # ─────────────────────────────────────────
            # CONTROLS SECTION (Play/Pause/Skip)
            # ─────────────────────────────────────────
            ctrl_y = time_y + 80
            ctrl_cx = (info_x + bar_x2) // 2
            
            # Main Play Button Circle
            draw.ellipse([ctrl_cx-40, ctrl_y-10, ctrl_cx+40, ctrl_y+70], fill=(160, 80, 255))
            # Pause Symbol (II)
            draw.text((ctrl_cx-12, ctrl_y+5), "II", font=self.ctrl_font, fill=(255, 255, 255))
            
            # Skip Buttons
            draw.text((ctrl_cx-130, ctrl_y+8), "⏮", font=self.ctrl_font, fill=(200, 180, 235))
            draw.text((ctrl_cx+90, ctrl_y+8), "⏭", font=self.ctrl_font, fill=(200, 180, 235))

            # Finalize
            final = bg.convert("RGB")
            final.save(output, quality=95)
            if os.path.exists(temp): os.remove(temp)
            return output

        except Exception:
            return config.DEFAULT_THUMB
