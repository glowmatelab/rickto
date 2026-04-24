# ==============================================================================
# _thumbnails.py - Cinematic Thumbnail Generator (Purple Galaxy Style)
# ==============================================================================

import os
import re
import asyncio
import aiohttp
import base64
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


class Thumbnail:
    def __init__(self):
        try:
            self.title_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 48)
            self.subtitle_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 26)
            self.regular_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 22)
            self.watermark_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 32)
            self.small_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 18)
        except OSError:
            self.title_font = self.subtitle_font = self.regular_font = \
                self.watermark_font = self.small_font = ImageFont.load_default()

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                with open(output_path, "wb") as f:
                    f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        try:
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

    def _paste_rounded(self, bg, img, pos, radius):
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, *img.size), radius, fill=255)
        bg.paste(img, pos, mask)

    def _generate_sync(self, temp: str, output: str, song: Track, size=(1280, 720)) -> str:
        try:
            W, H = size  # 1280 x 720

            # ─────────────────────────────────────────
            # 1. BACKGROUND
            # ─────────────────────────────────────────
            with Image.open(temp) as raw:
                bg = raw.resize((W, H)).convert("RGBA")

            bg = bg.filter(ImageFilter.GaussianBlur(25))

            # Dark purple overlay
            overlay = Image.new("RGBA", (W, H), (8, 0, 20, 200))
            bg = Image.alpha_composite(bg, overlay)

            # Purple vignette
            vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vdraw = ImageDraw.Draw(vignette)
            for i in range(60):
                alpha = int(160 * (i / 60))
                vdraw.rectangle([i, i, W - i, H - i], outline=(15, 0, 40, alpha))
            bg = Image.alpha_composite(bg, vignette)

            draw = ImageDraw.Draw(bg)

            # ─────────────────────────────────────────
            # 2. GALAXY BOTS WATERMARK — top right only
            # ─────────────────────────────────────────
            watermark = "GALAXY BOTS"
            pink_colors = [(255, 80, 180), (200, 60, 220), (255, 130, 220),
                          (180, 80, 255), (255, 80, 180), (200, 60, 220),
                          (255, 130, 220), (180, 80, 255), (255, 80, 180),
                          (200, 60, 220), (255, 130, 220)]

            rw = sum(self.watermark_font.getlength(c) for c in watermark)
            rx = W - rw - 40
            ry = 28
            cx = rx
            for i, char in enumerate(watermark):
                draw.text((cx + 1, ry + 1), char, font=self.watermark_font, fill=(0, 0, 0, 120))
                draw.text((cx, ry), char, font=self.watermark_font, fill=pink_colors[i % len(pink_colors)])
                cx += self.watermark_font.getlength(char)

            # ─────────────────────────────────────────
            # 3. GLASS PANEL
            # ─────────────────────────────────────────
            panel_x1 = 60
            panel_y1 = 340
            panel_x2 = W - 60
            panel_y2 = H - 40

            glass = Image.new("RGBA", (panel_x2 - panel_x1, panel_y2 - panel_y1), (25, 5, 55, 210))
            glass_mask = Image.new("L", glass.size, 0)
            ImageDraw.Draw(glass_mask).rounded_rectangle((0, 0, *glass.size), radius=30, fill=255)
            glass.putalpha(glass_mask)
            bg.paste(glass, (panel_x1, panel_y1), glass)

            # Glass border
            draw.rounded_rectangle(
                [panel_x1, panel_y1, panel_x2, panel_y2],
                radius=30,
                outline=(160, 60, 255, 200),
                width=2
            )

            # ─────────────────────────────────────────
            # 4. YOUTUBE THUMBNAIL — left inside panel
            # ─────────────────────────────────────────
            thumb_size = 220
            panel_h = panel_y2 - panel_y1
            thumb_x = panel_x1 + 35
            thumb_y = panel_y1 + (panel_h - thumb_size) // 2

            with Image.open(temp) as raw_thumb:
                thumb = raw_thumb.resize((thumb_size, thumb_size)).convert("RGBA")

            # Glow behind thumb
            glow = Image.new("RGBA", (thumb_size + 30, thumb_size + 30), (0, 0, 0, 0))
            ImageDraw.Draw(glow).rounded_rectangle(
                (0, 0, thumb_size + 30, thumb_size + 30),
                radius=25,
                fill=(160, 60, 255, 50)
            )
            bg.paste(glow, (thumb_x - 15, thumb_y - 15), glow)

            self._paste_rounded(bg, thumb, (thumb_x, thumb_y), radius=20)

            # Purple border around thumb
            draw.rounded_rectangle(
                [thumb_x - 2, thumb_y - 2,
                 thumb_x + thumb_size + 2, thumb_y + thumb_size + 2],
                radius=22,
                outline=(180, 80, 255, 255),
                width=2
            )

            # ─────────────────────────────────────────
            # 5. SONG INFO — right of thumbnail
            # ─────────────────────────────────────────
            info_x = thumb_x + thumb_size + 45
            info_y = panel_y1 + 28
            info_max_w = panel_x2 - info_x - 30

            # Music note
            draw.text((info_x, info_y), "♪", font=self.subtitle_font, fill=(200, 100, 255))

            # Song title
            title = re.sub(r"\W+", " ", song.title).title()
            title_trimmed = trim_to_width(title, self.title_font, info_max_w - 40)
            draw.text((info_x + 38, info_y - 6), title_trimmed, font=self.title_font, fill=(255, 255, 255))

            # Purple accent line
            title_h = self.title_font.size
            line_y = info_y + title_h + 4
            draw.rounded_rectangle(
                [info_x, line_y, info_x + 280, line_y + 3],
                radius=2,
                fill=(180, 80, 255)
            )

            # Views
            meta_y = line_y + 14
            views = song.view_count or "Unknown"
            draw.text(
                (info_x, meta_y),
                f"YouTube  •  {views}",
                font=self.regular_font,
                fill=(180, 150, 220)
            )

            # ─────────────────────────────────────────
            # 6. PROGRESS BAR
            # ─────────────────────────────────────────
            bar_x1 = info_x
            bar_x2 = panel_x2 - 35
            bar_y = meta_y + 48
            bar_h = 6
            bar_w = bar_x2 - bar_x1
            fill_w = int(bar_w * 0.38)

            # Track background
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x2, bar_y + bar_h],
                radius=3,
                fill=(60, 20, 90)
            )

            # Filled portion
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x1 + fill_w, bar_y + bar_h],
                radius=3,
                fill=(180, 80, 255)
            )

            # Glow dot
            dot_x = bar_x1 + fill_w
            dot_r = 8
            draw.ellipse(
                [dot_x - dot_r - 2, bar_y - dot_r,
                 dot_x + dot_r + 2, bar_y + dot_r + bar_h],
                fill=(180, 80, 255, 80)
            )
            draw.ellipse(
                [dot_x - dot_r + 3, bar_y - dot_r + 4,
                 dot_x + dot_r - 3, bar_y + dot_r + bar_h - 4],
                fill=(220, 150, 255)
            )

            # Time labels
            time_y = bar_y + bar_h + 10
            draw.text((bar_x1, time_y), "00:00", font=self.small_font, fill=(160, 120, 200))
            duration = getattr(song, 'duration', '00:00')
            dur_w = self.small_font.getlength(duration)
            draw.text((bar_x2 - dur_w, time_y), duration, font=self.small_font, fill=(160, 120, 200))

            # ─────────────────────────────────────────
            # 7. REQUESTED BY
            # ─────────────────────────────────────────
            req_y = time_y + 32
            requested_by = getattr(song, 'requested_by', None)
            if requested_by:
                name = getattr(requested_by, 'first_name', '') or str(requested_by)
                draw.text((info_x, req_y), "▸ ", font=self.small_font, fill=(180, 80, 255))
                draw.text((info_x + 18, req_y), f"Requested by  {name}", font=self.small_font, fill=(200, 170, 230))

            # ─────────────────────────────────────────
            # 8. SAVE
            # ─────────────────────────────────────────
            final = bg.convert("RGB")
            final.save(output, quality=95)

            try:
                os.remove(temp)
            except:
                pass

            return output

        except Exception:
            return config.DEFAULT_THUMB
