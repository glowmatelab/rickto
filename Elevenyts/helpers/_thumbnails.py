# ==============================================================================
# _thumbnails.py - Neon Detailed Thumbnail Generator (Purple Galaxy Style)
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


class Thumbnail:
    def __init__(self):
        try:
            self.title_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 52)
            self.nowplaying_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 24)
            self.regular_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 24)
            self.small_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 20)
        except OSError:
            self.title_font = self.nowplaying_font = \
                self.regular_font = self.small_font = ImageFont.load_default()

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

    def _paste_rounded_right(self, bg, img, pos, radius):
        """Rounded corners only on right side."""
        w, h = img.size
        mask = Image.new("L", img.size, 255)
        d = ImageDraw.Draw(mask)
        # Square left corners, rounded right corners
        d.rectangle([0, 0, w // 2, h], fill=255)
        d.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
        bg.paste(img, pos, mask)

    def _draw_neon_line(self, draw, x1, y1, x2, y2, color, width=2, glow=True):
        """Draw a neon glowing line."""
        if glow:
            # Outer glow
            r, g, b = color
            for i in range(4, 0, -1):
                alpha_color = (r, g, b)
                draw.line([(x1, y1), (x2, y2)],
                         fill=alpha_color, width=width + i * 2)
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

    def _generate_sync(self, temp: str, output: str, song: Track, size=(1280, 720)) -> str:
        try:
            W, H = size  # 1280 x 720

            # ─────────────────────────────────────────
            # 1. BASE CANVAS — pure dark background
            # ─────────────────────────────────────────
            canvas = Image.new("RGBA", (W, H), (5, 0, 15, 255))

            # Subtle radial purple glow in center-right
            glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_layer)
            for i in range(300, 0, -1):
                alpha = int(40 * (1 - i / 300))
                glow_draw.ellipse(
                    [W // 2 + 100 - i, H // 2 - i,
                     W // 2 + 100 + i, H // 2 + i],
                    fill=(100, 20, 200, alpha)
                )
            canvas = Image.alpha_composite(canvas, glow_layer)

            draw = ImageDraw.Draw(canvas)

            # ─────────────────────────────────────────
            # 2. LEFT SIDE — YouTube Thumbnail
            # ─────────────────────────────────────────
            thumb_w = 520
            thumb_h = H  # Full height

            with Image.open(temp) as raw:
                thumb = raw.resize((thumb_w, thumb_h)).convert("RGBA")

            # Slight blur on edges
            thumb_blurred = thumb.filter(ImageFilter.GaussianBlur(2))

            # Paste with rounded right corners
            self._paste_rounded_right(canvas, thumb_blurred, (0, 0), radius=40)

            # Dark gradient fade on right edge of thumbnail
            fade = Image.new("RGBA", (120, H), (0, 0, 0, 0))
            fade_draw = ImageDraw.Draw(fade)
            for i in range(120):
                alpha = int(255 * (i / 120))
                fade_draw.line([(i, 0), (i, H)], fill=(5, 0, 15, alpha))
            canvas.paste(fade, (thumb_w - 120, 0), fade)

            # Neon purple glow on right edge of thumbnail
            draw_canvas = ImageDraw.Draw(canvas)
            for i in range(8, 0, -1):
                alpha = int(180 * (i / 8))
                draw_canvas.line(
                    [(thumb_w - i, 0), (thumb_w - i, H)],
                    fill=(180, 60, 255),
                    width=1
                )

            # Bright neon divider line
            draw_canvas.line(
                [(thumb_w, 0), (thumb_w, H)],
                fill=(200, 80, 255),
                width=3
            )

            # ─────────────────────────────────────────
            # 3. RIGHT SIDE — Info Panel
            # ─────────────────────────────────────────
            right_x = thumb_w + 50
            right_max_w = W - right_x - 40

            # ── NOW PLAYING ──
            np_y = 80
            # Neon pink dot
            draw_canvas.ellipse(
                [right_x, np_y + 6, right_x + 14, np_y + 20],
                fill=(255, 80, 180)
            )
            # Glow around dot
            for i in range(6, 0, -1):
                draw_canvas.ellipse(
                    [right_x - i, np_y + 6 - i,
                     right_x + 14 + i, np_y + 20 + i],
                    outline=(255, 80, 180),
                    width=1
                )
            draw_canvas.text(
                (right_x + 24, np_y),
                "NOW PLAYING",
                font=self.nowplaying_font,
                fill=(255, 80, 180)
            )

            # ── SONG TITLE ──
            title_y = np_y + 55
            title = re.sub(r"\W+", " ", song.title).title()
            title_trimmed = trim_to_width(title, self.title_font, right_max_w)

            # Title shadow/glow
            for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
                draw_canvas.text(
                    (right_x + dx, title_y + dy),
                    title_trimmed,
                    font=self.title_font,
                    fill=(140, 40, 220)
                )
            # Title main
            draw_canvas.text(
                (right_x, title_y),
                title_trimmed,
                font=self.title_font,
                fill=(255, 255, 255)
            )

            # ── NEON ACCENT LINE UNDER TITLE ──
            accent_y = title_y + self.title_font.size + 10
            for i in range(5, 0, -1):
                draw_canvas.line(
                    [(right_x, accent_y + i),
                     (right_x + 320, accent_y + i)],
                    fill=(180, 60, 255),
                    width=1
                )
            draw_canvas.line(
                [(right_x, accent_y),
                 (right_x + 320, accent_y)],
                fill=(220, 100, 255),
                width=3
            )

            # ── VIEWS ──
            views_y = accent_y + 22
            views = song.view_count or "Unknown"
            draw_canvas.text(
                (right_x, views_y),
                f"YouTube  •  {views}",
                font=self.regular_font,
                fill=(180, 140, 230)
            )

            # ── PROGRESS BAR ──
            bar_x1 = right_x
            bar_x2 = W - 50
            bar_y = views_y + 70
            bar_h = 8
            bar_w = bar_x2 - bar_x1
            fill_w = int(bar_w * 0.38)

            # Track bg
            draw_canvas.rounded_rectangle(
                [bar_x1, bar_y, bar_x2, bar_y + bar_h],
                radius=4,
                fill=(40, 10, 70)
            )

            # Neon filled portion
            draw_canvas.rounded_rectangle(
                [bar_x1, bar_y, bar_x1 + fill_w, bar_y + bar_h],
                radius=4,
                fill=(180, 60, 255)
            )

            # Glow on filled bar
            for i in range(4, 0, -1):
                draw_canvas.rounded_rectangle(
                    [bar_x1, bar_y - i,
                     bar_x1 + fill_w, bar_y + bar_h + i],
                    radius=4,
                    outline=(180, 60, 255),
                    width=1
                )

            # Neon dot at progress
            dot_x = bar_x1 + fill_w
            dot_y = bar_y + bar_h // 2
            for r in range(12, 4, -2):
                alpha_fill = (180, 60, 255)
                draw_canvas.ellipse(
                    [dot_x - r, dot_y - r, dot_x + r, dot_y + r],
                    fill=alpha_fill
                )
            draw_canvas.ellipse(
                [dot_x - 6, dot_y - 6, dot_x + 6, dot_y + 6],
                fill=(230, 160, 255)
            )

            # Time labels
            time_y = bar_y + bar_h + 12
            draw_canvas.text(
                (bar_x1, time_y),
                "00:00",
                font=self.small_font,
                fill=(160, 110, 210)
            )
            duration = getattr(song, 'duration', '00:00')
            dur_w = self.small_font.getlength(duration)
            draw_canvas.text(
                (bar_x2 - dur_w, time_y),
                duration,
                font=self.small_font,
                fill=(160, 110, 210)
            )

            # ── REQUESTED BY ──
            req_y = time_y + 55
            requested_by = getattr(song, 'requested_by', None)
            if requested_by:
                name = getattr(requested_by, 'first_name', '') or str(requested_by)

                # Neon arrow
                draw_canvas.text(
                    (right_x, req_y),
                    "▸",
                    font=self.small_font,
                    fill=(255, 80, 180)
                )
                # Glow on arrow
                draw_canvas.text(
                    (right_x, req_y),
                    "▸",
                    font=self.small_font,
                    fill=(255, 80, 180)
                )
                draw_canvas.text(
                    (right_x + 24, req_y),
                    "Requested by",
                    font=self.small_font,
                    fill=(160, 110, 210)
                )
                # Name in neon pink
                name_x = right_x + 24 + self.small_font.getlength("Requested by  ")
                draw_canvas.text(
                    (name_x, req_y),
                    name,
                    font=self.small_font,
                    fill=(255, 120, 200)
                )

            # ── BOTTOM NEON LINE ──
            for i in range(4, 0, -1):
                draw_canvas.line(
                    [(0, H - i), (W, H - i)],
                    fill=(180, 60, 255),
                    width=1
                )
            draw_canvas.line(
                [(0, H - 4), (W, H - 4)],
                fill=(220, 100, 255),
                width=3
            )

            # ─────────────────────────────────────────
            # 4. SAVE
            # ─────────────────────────────────────────
            final = canvas.convert("RGB")
            final.save(output, quality=95)

            try:
                os.remove(temp)
            except:
                pass

            return output

        except Exception:
            return config.DEFAULT_THUMB
