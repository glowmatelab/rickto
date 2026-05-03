import os
import re
import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Fonts path (Ensure these exist)
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
        except:
            self.title_font = self.artist_font = self.time_font = ImageFont.load_default()

    def _generate_sync(self, temp, output, song, size=(1280, 720)):
        W, H = size
        
        # 1. Background: Deep Blur + Dark Overlay
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
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, *art.size), 40, fill=255)
        bg.paste(art, (margin, margin), mask)

        # 3. Right Side Setup
        right_start_x = margin + thumb_size + 80
        right_width = W - right_start_x - 80
        center_x = right_start_x + (right_width // 2)

        # Title & Artist (Left Aligned in the right section)
        clean_title = song.title[:25] + "..." if len(song.title) > 25 else song.title
        draw.text((right_start_x, 140), clean_title, font=self.title_font, fill=(255, 255, 255))
        draw.text((right_start_x, 200), "Antavion • YouTube", font=self.artist_font, fill=(180, 180, 180))

        # 4. Progress Bar Section
        bar_y = 310
        bar_h = 8
        draw.rounded_rectangle([right_start_x, bar_y, right_start_x + right_width, bar_y + bar_h], radius=4, fill=(255, 255, 255, 60))
        # Active Progress (approx 35%)
        draw.rounded_rectangle([right_start_x, bar_y, right_start_x + (right_width * 0.35), bar_y + bar_h], radius=4, fill=(255, 255, 255, 200))

        # Timestamps
        draw.text((right_start_x, bar_y + 25), "0:03", font=self.time_font, fill=(150, 150, 150))
        duration = getattr(song, 'duration', '5:39')
        draw.text((right_start_x + right_width - 60, bar_y + 25), f"-{duration}", font=self.time_font, fill=(150, 150, 150))

        # Jerry/Antavion Bots Badge (Floating on bar)
        badge_text = "ANTAVION"
        bw = self.badge_font.getlength(badge_text) + 20
        draw.rounded_rectangle([center_x - (bw/2), bar_y - 12, center_x + (bw/2), bar_y + 20], radius=10, fill=(80, 80, 80, 180))
        draw.text((center_x - (bw/2) + 10, bar_y - 8), badge_text, font=self.badge_font, fill=(255, 255, 255))

        # 5. Main Controls (Centered)
        ctrl_y = 450
        # Rewind (<<)
        draw.text((center_x - 180, ctrl_y + 10), "◄◄", font=self.icon_font_md, fill=(255, 255, 255))
        # Pause (||)
        draw.text((center_x - 25, ctrl_y), "||", font=self.icon_font_lg, fill=(255, 255, 255))
        # Forward (>>)
        draw.text((center_x + 130, ctrl_y + 10), "►►", font=self.icon_font_md, fill=(255, 255, 255))

        # 6. Volume Slider
        vol_y = 600
        vol_bar_w = right_width * 0.7
        vol_start_x = center_x - (vol_bar_w // 2)
        
        # Volume Icons
        draw.text((vol_start_x - 40, vol_y - 5), "低", font=self.time_font, fill=(180, 180, 180)) # Simple placeholder for speaker
        draw.text((vol_start_x + vol_bar_w + 15, vol_y - 5), "高", font=self.time_font, fill=(180, 180, 180))

        # Vol Bar
        draw.rounded_rectangle([vol_start_x, vol_y, vol_start_x + vol_bar_w, vol_y + 4], radius=2, fill=(255, 255, 255, 60))
        draw.rounded_rectangle([vol_start_x, vol_y, vol_start_x + (vol_bar_w * 0.8), vol_y + 4], radius=2, fill=(255, 255, 255, 200))
        # Vol Dot
        dot_x = vol_start_x + (vol_bar_w * 0.8)
        draw.ellipse([dot_x - 6, vol_y - 4, dot_x + 6, vol_y + 8], fill=(255, 255, 255))

        # 7. Bottom Icons (Lyric & Queue)
        draw.text((right_start_x + 50, 680), "💬", font=self.artist_font, fill=(255, 255, 255, 150))
        draw.text((right_start_x + right_width - 80, 680), "☰", font=self.artist_font, fill=(255, 255, 255, 150))

        # Save
        final = bg.convert("RGB")
        final.save(output, quality=100, subsampling=0)
        return output
