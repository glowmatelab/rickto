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


def decode_text(encoded: str) -> str:
    return base64.b64decode(encoded).decode("utf-8")


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
                "Elevenyts/helpers/Raleway-Bold.ttf", 36)

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

    def _draw_rounded_rect(self, draw, xy, radius, fill, outline=None, outline_width=2):
        """Draw a filled rounded rectangle."""
        x1, y1, x2, y2 = xy
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=outline_width)

    def _paste_rounded(self, bg, img, pos, radius):
        """Paste image with rounded corners mask."""
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, *img.size), radius, fill=255)
        bg.paste(img, pos, mask)

    def _generate_sync(self, temp: str, output: str, song: Track, size=(1280, 720)) -> str:
        try:
            W, H = size  # 1280 x 720

            # ─────────────────────────────────────────
            # 1. BACKGROUND — blurred + dark purple overlay
            # ─────────────────────────────────────────
            with Image.open(temp) as raw:
                bg = raw.resize((W, H)).convert("RGBA")

            bg = bg.filter(ImageFilter.GaussianBlur(28))

            # Dark purple overlay
            overlay = Image.new("RGBA", (W, H), (10, 0, 25, 210))
            bg = Image.alpha_composite(bg, overlay)

            # Subtle purple vignette edges
            vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vdraw = ImageDraw.Draw(vignette)
            for i in range(80):
                alpha = int(180 * (i / 80))
                color = (20, 0, 50, alpha)
                vdraw.rectangle([i, i, W - i, H - i], outline=color)
            bg = Image.alpha_composite(bg, vignette)

            draw = ImageDraw.Draw(bg)

            # ─────────────────────────────────────────
            # 2. WATERMARKS — top corners
            # ─────────────────────────────────────────
            left_text = decode_text("QVJUSVNU")      # ARTIST
            right_text = decode_text("RUxFVkVOWVRT")  # ELEVENYTS

            purple_colors = [(180, 80, 255), (130, 60, 220), (220, 120, 255)]
            pink_colors = [(255, 80, 180), (200, 60, 220), (255, 130, 220)]

            # Left watermark — ARTIST
            lx, ly = 40, 28
            cx = lx
            for i, char in enumerate(left_text):
                draw.text((cx + 1, ly + 1), char, font=self.watermark_font, fill=(0, 0, 0, 120))
                draw.text((cx, ly), char, font=self.watermark_font, fill=purple_colors[i % 3])
                cx += self.watermark_font.getlength(char)

            # Right watermark — ELEVENYTS
            rw = sum(self.watermark_font.getlength(c) for c in right_text)
            rx = W - rw - 40
            ry = 28
            cx = rx
            for i, char in enumerate(right_text):
                draw.text((cx + 1, ry + 1), char, font=self.watermark_font, fill=(0, 0, 0, 120))
                draw.text((cx, ry), char, font=self.watermark_font, fill=pink_colors[i % 3])
                cx += self.watermark_font.getlength(char)

            # ─────────────────────────────────────────
            # 3. GLASS PANEL — centered bottom area
            # ─────────────────────────────────────────
            panel_x1, panel_y1 = 60, 380
            panel_x2, panel_y2 = W - 60, H - 40

            # Glass background
            glass = Image.new("RGBA", (panel_x2 - panel_x1, panel_y2 - panel_y1), (30, 5, 60, 200))
            glass_mask = Image.new("L", glass.size, 0)
            ImageDraw.Draw(glass_mask).rounded_rectangle((0, 0, *glass.size), radius=30, fill=255)
            glass.putalpha(glass_mask)
            bg.paste(glass, (panel_x1, panel_y1), glass)

            # Glass border — purple glow
            draw.rounded_rectangle(
                [panel_x1, panel_y1, panel_x2, panel_y2],
                radius=30,
                outline=(160, 60, 255, 180),
                width=2
            )

            # ─────────────────────────────────────────
            # 4. YOUTUBE THUMBNAIL — left inside panel
            # ─────────────────────────────────────────
            thumb_size = 200
            thumb_x = panel_x1 + 30
            thumb_y = panel_y1 + ((panel_y2 - panel_y1) - thumb_size) // 2

            with Image.open(temp) as raw_thumb:
                thumb = raw_thumb.resize((thumb_size, thumb_size)).convert("RGBA")

            # Glow behind thumb
            glow = Image.new("RGBA", (thumb_size + 20, thumb_size + 20), (0, 0, 0, 0))
            ImageDraw.Draw(glow).rounded_rectangle(
                (0, 0, thumb_size + 20, thumb_size + 20),
                radius=22,
                fill=(160, 60, 255, 60)
            )
            bg.paste(glow, (thumb_x - 10, thumb_y - 10), glow)

            self._paste_rounded(bg, thumb, (thumb_x, thumb_y), radius=18)

            # Purple border around thumb
            draw.rounded_rectangle(
                [thumb_x - 2, thumb_y - 2, thumb_x + thumb_size + 2, thumb_y + thumb_size + 2],
                radius=20,
                outline=(180, 80, 255, 255),
                width=2
            )

            # ─────────────────────────────────────────
            # 5. SONG INFO — right of thumbnail
            # ─────────────────────────────────────────
            info_x = thumb_x + thumb_size + 40
            info_y = panel_y1 + 30
            info_max_w = panel_x2 - info_x - 30

            # Music note icon before title
            draw.text((info_x, info_y), "♪", font=self.subtitle_font, fill=(200, 100, 255))
            title_x = info_x + 35

            # Song title
            title = re.sub(r"\W+", " ", song.title).title()
            title_trimmed = trim_to_width(title, self.title_font, info_max_w - 35)
            draw.text((title_x, info_y - 4), title_trimmed, font=self.title_font, fill=(255, 255, 255))

            # Thin purple accent line under title
            title_h = self.title_font.size
            line_y = info_y + title_h + 6
            draw.rounded_rectangle(
                [info_x, line_y, info_x + 300, line_y + 3],
                radius=2,
                fill=(180, 80, 255)
            )

            # Views + platform
            meta_y = line_y + 16
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
            bar_x2 = panel_x2 - 30
            bar_y = meta_y + 52
            bar_h = 6
            bar_w = bar_x2 - bar_x1
            fill_w = int(bar_w * 0.38)  # Static 38% filled

            # Track background
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x2, bar_y + bar_h],
                radius=3,
                fill=(60, 20, 90)
            )

            # Filled portion — purple gradient effect
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x1 + fill_w, bar_y + bar_h],
                radius=3,
                fill=(180, 80, 255)
            )

            # Glow dot at progress point
            dot_x = bar_x1 + fill_w
            dot_r = 8
            # Outer glow
            draw.ellipse(
                [dot_x - dot_r - 3, bar_y - dot_r - 1, dot_x + dot_r + 3, bar_y + dot_r + bar_h + 1],
                fill=(180, 80, 255, 80)
            )
            # Inner dot
            draw.ellipse(
                [dot_x - dot_r + 2, bar_y - dot_r + 3, dot_x + dot_r - 2, bar_y + dot_r + bar_h - 3],
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
            req_y = time_y + 30
            requested_by = getattr(song, 'requested_by', None)
            if requested_by:
                name = getattr(requested_by, 'first_name', '') or str(requested_by)
                req_text = f"Requested by  {name}"
                draw.text((info_x, req_y), "▸ ", font=self.small_font, fill=(180, 80, 255))
                draw.text((info_x + 16, req_y), req_text, font=self.small_font, fill=(200, 170, 230))

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
