# ==============================================================================
# Final Code - Dynamic Title Scaling & Real Blur BG (No Branding)
# ==============================================================================

import os
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from Elevenyts import config

# Fonts path
FONT_BOLD = "Elevenyts/helpers/Raleway-Bold.ttf"
FONT_REG = "Elevenyts/helpers/Inter-Light.ttf"

class Thumbnail:
    def __init__(self):
        try:
            self.title_font_path = FONT_BOLD
            self.artist_font = ImageFont.truetype(FONT_REG, 30)
            self.time_font = ImageFont.truetype(FONT_REG, 22)
            self.badge_font = ImageFont.truetype(FONT_BOLD, 18)
        except OSError:
            self.title_font_path = None
            self.artist_font = self.time_font = self.badge_font = ImageFont.load_default()

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
            # 1. Background: Real Thumbnail Blur
            with Image.open(temp) as raw:
                bg = raw.convert("RGBA").resize((W, H))
                bg = bg.filter(ImageFilter.GaussianBlur(100)) 
                overlay = Image.new("RGBA", (W, H), (0, 0, 0, 160))
                bg = Image.alpha_composite(bg, overlay)

            draw = ImageDraw.Draw(bg)

            # 2. Left Side: Rounded Artwork
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

            # 3. Right Side Info Area
            right_x = margin + thumb_size + 85
            right_w = W - right_x - 80
            center_x = right_x + (right_w // 2)

            # --- DYNAMIC TITLE SCALING ---
            title_text = song.title
            current_font_size = 45
            
            if self.title_font_path:
                title_font = ImageFont.truetype(self.title_font_path, current_font_size)
                # Check if title exceeds width, then shrink font
                while title_font.getlength(title_text) > right_w and current_font_size > 25:
                    current_font_size -= 2
                    title_font = ImageFont.truetype(self.title_font_path, current_font_size)
                
                # Final Truncation if still too long
                if title_font.getlength(title_text) > right_w:
                    while title_font.getlength(title_text + "...") > right_w:
                        title_text = title_text[:-1]
                    title_text += "..."
            else:
                title_font = ImageFont.load_default()

            draw.text((right_x, 130), title_text, font=title_font, fill=(255, 255, 255))
            
            # Subtitle: Views and YouTube
            views = getattr(song, 'view_count', '0')
            draw.text((right_x, 195), f"{views} views • YouTube", font=self.artist_font, fill=(180, 180, 180))

            # 4. Progress Bar & MUSIC Badge
            bar_y = 320
            draw.rounded_rectangle([right_x, bar_y, right_x + right_w, bar_y + 7], radius=4, fill=(255, 255, 255, 60))
            # Fixed bar to 40% for visual aesthetics
            draw.rounded_rectangle([right_x, bar_y, right_x + (right_w * 0.4), bar_y + 7], radius=4, fill=(255, 255, 255, 220))

            badge_text = "MUSIC"
            bw = self.badge_font.getlength(badge_text) + 20
            draw.rounded_rectangle([center_x - (bw/2), bar_y - 12, center_x + (bw/2), bar_y + 18], radius=8, fill=(60, 60, 60, 220))
            draw.text((center_x - (bw/2) + 10, bar_y - 9), badge_text, font=self.badge_font, fill=(255, 255, 255))

            # Timestamps
            draw.text((right_x, bar_y + 25), "0:00", font=self.time_font, fill=(160, 160, 160))
            dur = getattr(song, 'duration', '04:30')
            draw.text((right_x + right_w - 70, bar_y + 25), f"-{dur}", font=self.time_font, fill=(160, 160, 160))

            # 5. Drawing Symbols (Manual Shapes)
            ctrl_y = 450
            # Pause Icon
            draw.rectangle([center_x - 15, ctrl_y, center_x - 3, ctrl_y + 50], fill=(255, 255, 255))
            draw.rectangle([center_x + 3, ctrl_y, center_x + 15, ctrl_y + 50], fill=(255, 255, 255))

            def draw_tri(x, y, size, direction='left'):
                pts = [(x, y + size/2), (x + size, y), (x + size, y + size)] if direction == 'left' else [(x + size, y + size/2), (x, y), (x, y + size)]
                draw.polygon(pts, fill=(255, 255, 255))

            # Skip/Back Icons
            draw_tri(center_x - 160, ctrl_y + 10, 30, 'left')
            draw_tri(center_x - 135, ctrl_y + 10, 30, 'left')
            draw_tri(center_x + 105, ctrl_y + 10, 30, 'right')
            draw_tri(center_x + 130, ctrl_y + 10, 30, 'right')

            # 6. Volume Slider
            vol_y = 590
            vol_bar_w = right_w * 0.75
            vx = center_x - (vol_bar_w // 2)
            draw.rounded_rectangle([vx, vol_y, vx + vol_bar_w, vol_y + 5], radius=3, fill=(255, 255, 255, 50))
            draw.rounded_rectangle([vx, vol_y, vx + (vol_bar_w * 0.7), vol_y + 5], radius=3, fill=(255, 255, 255, 180))
            draw.ellipse([vx + (vol_bar_w * 0.7) - 8, vol_y - 6, vx + (vol_bar_w * 0.7) + 8, vol_y + 10], fill=(255, 255, 255))

            # 7. Bottom Icons (Layout/Queue)
            lx, ly = right_x + 60, 670
            draw.rounded_rectangle([lx, ly, lx+35, ly+25], radius=5, outline=(255, 255, 255, 150), width=2)
            qx, qy = right_x + right_w - 90, 670
            for i in range(3):
                draw.line([qx, qy + (i*8), qx+30, qy + (i*8)], fill=(255, 255, 255, 150), width=3)

            final = bg.convert("RGB")
            final.save(output, quality=95)
            if os.path.exists(temp): os.remove(temp)
            return output
            
        except Exception as e:
            print(f"Drawing Error: {e}")
            return config.DEFAULT_THUMB
