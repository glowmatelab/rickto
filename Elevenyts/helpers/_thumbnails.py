# ==============================================================================
# Elevenyts - Final Apple Music Style (Blur BG + Views + Symbols)
# ==============================================================================

import os
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from Elevenyts import config

# Fonts - Inka path check kar lena helpers folder mein
FONT_BOLD = "Elevenyts/helpers/Raleway-Bold.ttf"
FONT_REG = "Elevenyts/helpers/Inter-Light.ttf"

class Thumbnail:
    def __init__(self):
        try:
            self.title_font = ImageFont.truetype(FONT_BOLD, 45)
            self.artist_font = ImageFont.truetype(FONT_REG, 30)
            self.time_font = ImageFont.truetype(FONT_REG, 22)
            self.badge_font = ImageFont.truetype(FONT_BOLD, 18)
        except OSError:
            self.title_font = self.artist_font = self.time_font = self.badge_font = ImageFont.load_default()

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(output_path, "wb") as f:
                        f.write(await resp.read())
        return output_path

    async def generate(self, song, size=(1280, 720)) -> str:
        try:
            if not os.path.exists("cache"):
                os.makedirs("cache")
            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_final.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)
            return await asyncio.get_event_loop().run_in_executor(
                None, self._generate_sync, temp, output, song, size
            )
        except Exception as e:
            print(f"Error: {e}")
            return config.DEFAULT_THUMB

    def _generate_sync(self, temp, output, song, size):
        W, H = size
        try:
            # 1. Background: Full Blur Image + Dark Overlay for Text Contrast
            with Image.open(temp) as raw:
                bg = raw.convert("RGBA").resize((W, H))
                bg = bg.filter(ImageFilter.GaussianBlur(100)) # Deep Blur
                overlay = Image.new("RGBA", (W, H), (0, 0, 0, 165)) # Darker tint
                bg = Image.alpha_composite(bg, overlay)

            draw = ImageDraw.Draw(bg)

            # 2. Left Side: Rounded Square Artwork
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

            # 3. Text Info Section
            right_x = margin + thumb_size + 85
            right_w = W - right_x - 80
            center_x = right_x + (right_w // 2)

            # Title
            clean_title = song.title[:28] + "..." if len(song.title) > 28 else song.title
            draw.text((right_x, 130), clean_title, font=self.title_font, fill=(255, 255, 255))
            
            # Views (Antavion Removed)
            views = getattr(song, 'view_count', 'Unknown')
            draw.text((right_x, 195), f"{views} views • YouTube", font=self.artist_font, fill=(180, 180, 180))

            # 4. Progress Bar & "MUSIC" Badge
            bar_y = 320
            draw.rounded_rectangle([right_x, bar_y, right_x + right_w, bar_y + 7], radius=4, fill=(255, 255, 255, 60))
            draw.rounded_rectangle([right_x, bar_y, right_x + (right_w * 0.4), bar_y + 7], radius=4, fill=(255, 255, 255, 220))

            badge_text = "MUSIC"
            bw = self.badge_font.getlength(badge_text) + 20
            draw.rounded_rectangle([center_x - (bw/2), bar_y - 12, center_x + (bw/2), bar_y + 18], radius=8, fill=(60, 60, 60, 220))
            draw.text((center_x - (bw/2) + 10, bar_y - 9), badge_text, font=self.badge_font, fill=(255, 255, 255))

            # Timestamps
            draw.text((right_x, bar_y + 25), "0:03", font=self.time_font, fill=(160, 160, 160))
            dur = getattr(song, 'duration', '4:30')
            draw.text((right_x + right_w - 70, bar_y + 25), f"-{dur}", font=self.time_font, fill=(160, 160, 160))

            # 5. DRAWING SYMBOLS (No Fonts Needed - Geometric Shapes)
            ctrl_y = 450
            # Pause Button
            draw.rectangle([center_x - 15, ctrl_y, center_x - 3, ctrl_y + 50], fill=(255, 255, 255))
            draw.rectangle([center_x + 3, ctrl_y, center_x + 15, ctrl_y + 50], fill=(255, 255, 255))

            # Rewind & Forward Triangles
            def draw_tri(x, y, size, direction='left'):
                if direction == 'left':
                    pts = [(x, y + size/2), (x + size, y), (x + size, y + size)]
                else:
                    pts = [(x + size, y + size/2), (x, y), (x, y + size)]
                draw.polygon(pts, fill=(255, 255, 255))

            draw_tri(center_x - 160, ctrl_y + 10, 30, 'left')
            draw_tri(center_x - 135, ctrl_y + 10, 30, 'left')
            draw_tri(center_x + 105, ctrl_y + 10, 30, 'right')
            draw_tri(center_x + 130, ctrl_y + 10, 30, 'right')

            # 6. Volume Slider
            vol_y = 590
            vol_bar_w = right_w * 0.75
            vx_start = center_x - (vol_bar_w // 2)
            draw.rounded_rectangle([vx_start, vol_y, vx_start + vol_bar_w, vol_y + 5], radius=3, fill=(255, 255, 255, 50))
            draw.rounded_rectangle([vx_start, vol_y, vx_start + (vol_bar_w * 0.7), vol_y + 5], radius=3, fill=(255, 255, 255, 180))
            # Vol Circle Indicator
            dot_x = vx_start + (vol_bar_w * 0.7)
            draw.ellipse([dot_x - 8, vol_y - 6, dot_x + 8, vol_y + 10], fill=(255, 255, 255))

            # 7. Bottom UI Symbols
            lx, ly = right_x + 60, 670
            draw.rounded_rectangle([lx, ly, lx+35, ly+25], radius=5, outline=(255, 255, 255, 150), width=2)
            qx, qy = right_x + right_w - 90, 670
            for i in range(3):
                draw.line([qx, qy + (i*8), qx+30, qy + (i*8)], fill=(255, 255, 255, 150), width=3)

            # Final Save
            final = bg.convert("RGB")
            final.save(output, quality=95)
            if os.path.exists(temp): os.remove(temp)
            return output
            
        except Exception as e:
            print(f"Drawing Error: {e}")
            return config.DEFAULT_THUMB
