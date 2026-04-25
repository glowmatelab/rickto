# ==============================================================================
# _thumbnails.py - Ultra-Premium Glassmorphism Edition
# ==============================================================================

import os
import re
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageColor

# ... (trim_to_width aur square_crop same rahenge) ...

class Thumbnail:
    def __init__(self):
        # Using slightly different sizes for better hierarchy
        try:
            self.brand_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 24)
            self.title_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 65)
            self.artist_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 36)
            self.time_font = ImageFont.truetype("Elevenyts/helpers/Inter-Light.ttf", 24)
            self.ctrl_font = ImageFont.truetype("Elevenyts/helpers/Raleway-Bold.ttf", 55)
        except OSError:
            self.brand_font = self.title_font = self.artist_font = \
                self.time_font = self.ctrl_font = ImageFont.load_default()

    def _get_dominant_color(self, img):
        """Image se main color nikalne ke liye (for dynamic theme)"""
        small_img = img.resize((1, 1))
        color = small_img.getpixel((0, 0))
        return color[:3] # RGB only

    def _generate_sync(self, temp, output, song, size=(1280, 720)):
        try:
            W, H = size
            with Image.open(temp) as raw:
                raw_rgba = raw.convert("RGBA")
                dom_color = self._get_dominant_color(raw_rgba)
                # Accent color based on image or default purple
                accent = dom_color if sum(dom_color) > 100 else (180, 100, 255)
                
                # Background with subtle blur
                bg = raw.resize((W, H)).filter(ImageFilter.GaussianBlur(12))

            # Darken Background slightly
            overlay = Image.new("RGBA", (W, H), (10, 10, 15, 140))
            bg = Image.alpha_composite(bg, overlay)

            # --- GLASS BOX ---
            bx1, by1, bx2, by2 = 80, 100, W - 80, H - 100
            
            # 1. Shadow Layer
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow)
            sd.rounded_rectangle([bx1+15, by1+15, bx2+15, by2+15], radius=45, fill=(0, 0, 0, 180))
            bg = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(25)))

            # 2. Glass Surface (Transparent & Blurry)
            draw = ImageDraw.Draw(bg)
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=45, fill=(30, 30, 40, 160))
            # Subtle White Border for Glass effect
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=45, outline=(255, 255, 255, 40), width=2)

            # --- DYNAMIC ART CIRCLE ---
            circle_r, cx, cy = 220, bx1 + 240, H // 2
            
            # Dynamic Outer Glow
            glow_color = accent + (80,)
            draw.ellipse([cx-circle_r-15, cy-circle_r-15, cx+circle_r+15, cy+circle_r+15], outline=glow_color, width=4)
            
            with Image.open(temp) as thumb:
                img_t = square_crop(thumb.convert("RGBA")).resize((circle_r*2, circle_r*2), Image.LANCZOS)
                mask = Image.new("L", (circle_r*2, circle_r*2), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, circle_r*2, circle_r*2), fill=255)
                bg.paste(img_t, (cx - circle_r, cy - circle_r), mask)

            # --- TEXT & INFO ---
            info_x = cx + circle_r + 70
            info_max_w = bx2 - info_x - 40

            # Dynamic Title
            title_raw = re.sub(r"\W+", " ", song.title).title()
            title_wrapped = self._wrap_title(title_raw, self.title_font, info_max_w)
            
            ty = by1 + 70
            for i, line in enumerate(title_wrapped):
                draw.text((info_x, ty + i*70), line, font=self.title_font, fill=(255, 255, 255))

            # Views with Icon-like pipe
            artist_y = ty + (len(title_wrapped) * 75) + 5
            draw.text((info_x, artist_y), f"● YouTube | {song.view_count or 'N/A'}", font=self.artist_font, fill=(accent[0], accent[1], accent[2], 200))

            # --- DYNAMIC PROGRESS BAR ---
            bar_y = artist_y + 90
            bar_x1, bar_x2 = info_x, bx2 - 70
            
            # Track
            draw.rounded_rectangle([bar_x1, bar_y, bar_x2, bar_y+8], radius=4, fill=(255, 255, 255, 25))
            # Dynamic Fill
            draw.rounded_rectangle([bar_x1, bar_y, bar_x1 + int((bar_x2-bar_x1)*0.4), bar_y+8], radius=4, fill=accent)
            
            # Knob with Glow
            kx = bar_x1 + int((bar_x2-bar_x1)*0.4)
            draw.ellipse([kx-12, bar_y-8, kx+12, bar_y+16], fill=accent)
            draw.ellipse([kx-6, bar_y-2, kx+6, bar_y+10], fill=(255, 255, 255))

            # --- MODERN CONTROLS ---
            ctrl_y = by2 - 90
            mid_x = (info_x + bar_x2) // 2
            
            # Shuffle & Repeat (Symbols)
            draw.text((info_x, ctrl_y), "⇄", font=self.time_font, fill=(200, 200, 200, 150))
            draw.text((bar_x2-30, ctrl_y), "↺", font=self.time_font, fill=(200, 200, 200, 150))

            # Play Button (Neon Style)
            draw.ellipse([mid_x-45, ctrl_y-15, mid_x+45, ctrl_y+75], fill=(accent[0], accent[1], accent[2], 40), outline=accent, width=3)
            # Draw Pause II
            draw.text((mid_x-14, ctrl_y+5), "II", font=self.ctrl_font, fill=(255, 255, 255))
            
            # Skips
            draw.text((mid_x-140, ctrl_y+8), "⏮", font=self.ctrl_font, fill=(255, 255, 255, 180))
            draw.text((mid_x+90, ctrl_y+8), "⏭", font=self.ctrl_font, fill=(255, 255, 255, 180))

            # Final Touch: Save
            bg.convert("RGB").save(output, quality=95)
            if os.path.exists(temp): os.remove(temp)
            return output

        except Exception as e:
            print(f"Error: {e}")
            return config.DEFAULT_THUMB
