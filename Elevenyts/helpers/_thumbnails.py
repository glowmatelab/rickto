# ==============================================================================
# _thumbnails.py - Premium Thumbnail Generator
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
    """Center crop image to square without stretching."""
    w, h = img.size
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    return img.crop((left, top, left + min_side, top + min_side))


class Thumbnail:
    def __init__(self):
        try:
            self.title_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 52)
            self.nowplaying_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 22)
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

    def _paste_rounded(self, bg, img, pos, radius):
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, *img.size), radius, fill=255)
        bg.paste(img, pos, mask)

    def _draw_glass_panel(self, canvas, x1, y1, x2, y2, radius=28,
                          fill=(18, 8, 38, 220), border=(255, 255, 255, 25)):
        # Shadow
        shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        for i in range(20, 0, -1):
            alpha = int(100 * (i / 20))
            shadow_draw.rounded_rectangle(
                [x1 + i, y1 + i, x2 + i, y2 + i],
                radius=radius,
                fill=(0, 0, 0, alpha)
            )
        merged = Image.alpha_composite(canvas, shadow_layer)
        canvas.paste(merged, (0, 0))

        # Glass fill
        glass = Image.new("RGBA", (x2 - x1, y2 - y1), fill)
        glass_mask = Image.new("L", glass.size, 0)
        ImageDraw.Draw(glass_mask).rounded_rectangle(
            (0, 0, *glass.size), radius=radius, fill=255)
        glass.putalpha(glass_mask)
        canvas.paste(glass, (x1, y1), glass)

        # Border
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=radius,
            outline=border,
            width=1
        )

        # Top highlight
        hl_w = x2 - x1 - radius * 2
        if hl_w > 0:
            highlight = Image.new("RGBA", (hl_w, 2), (255, 255, 255, 35))
            canvas.paste(highlight, (x1 + radius, y1 + 2), highlight)

    def _generate_sync(self, temp: str, output: str, song: Track, size=(1280, 720)) -> str:
        try:
            W, H = size  # 1280 x 720

            # ─────────────────────────────────────────
            # 1. BACKGROUND
            # ─────────────────────────────────────────
            with Image.open(temp) as raw:
                bg = raw.resize((W, H)).convert("RGBA")

            bg = bg.filter(ImageFilter.GaussianBlur(30))

            # Dark overlay
            overlay = Image.new("RGBA", (W, H), (5, 2, 15, 200))
            bg = Image.alpha_composite(bg, overlay)

            # Vignette
            vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vdraw = ImageDraw.Draw(vignette)
            for i in range(100):
                alpha = int(160 * (i / 100))
                vdraw.rectangle(
                    [i, i, W - i, H - i],
                    outline=(0, 0, 0, alpha)
                )
            bg = Image.alpha_composite(bg, vignette)

            # ─────────────────────────────────────────
            # 2. THUMBNAIL PANEL — left, full height
            # ─────────────────────────────────────────
            tp_x1 = 40
            tp_y1 = 40
            tp_x2 = 360
            tp_y2 = H - 40

            self._draw_glass_panel(
                bg, tp_x1, tp_y1, tp_x2, tp_y2,
                radius=28,
                fill=(15, 6, 32, 225),
                border=(255, 255, 255, 28)
            )

            # Square crop thumbnail
            with Image.open(temp) as raw_thumb:
                cropped = square_crop(raw_thumb.convert("RGBA"))
                thumb_size = tp_x2 - tp_x1 - 40  # 280px
                thumb = cropped.resize((thumb_size, thumb_size))

            # Vertically center thumb in panel
            thumb_x = tp_x1 + 20
            thumb_y = tp_y1 + (tp_y2 - tp_y1 - thumb_size) // 2

            self._paste_rounded(bg, thumb, (thumb_x, thumb_y), radius=20)

            # ─────────────────────────────────────────
            # 3. INFO PANEL — right, full height
            # ─────────────────────────────────────────
            ip_x1 = tp_x2 + 30
            ip_y1 = 40
            ip_x2 = W - 40
            ip_y2 = H - 40

            self._draw_glass_panel(
                bg, ip_x1, ip_y1, ip_x2, ip_y2,
                radius=28,
                fill=(15, 6, 32, 225),
                border=(255, 255, 255, 28)
            )

            draw = ImageDraw.Draw(bg)
            info_x = ip_x1 + 45
            info_max_w = ip_x2 - info_x - 35
            panel_h = ip_y2 - ip_y1

            # Vertical center start point
            content_h = (
                14 +   # now playing
                38 +   # gap
                58 +   # title
                14 +   # accent line
                18 +   # views gap
                28 +   # views
                55 +   # progress bar gap
                25 +   # bar + dot
                15 +   # time
                40 +   # requested by gap
                24     # requested by
            )
            start_y = ip_y1 + (panel_h - content_h) // 2

            # ── NOW PLAYING ──
            np_y = start_y
            draw.ellipse(
                [info_x, np_y + 5, info_x + 12, np_y + 17],
                fill=(160, 80, 255)
            )
            draw.text(
                (info_x + 20, np_y),
                "NOW PLAYING",
                font=self.nowplaying_font,
                fill=(160, 80, 255)
            )

            # ── SONG TITLE ──
            title_y = np_y + 50
            title = re.sub(r"\W+", " ", song.title).title()
            title_trimmed = trim_to_width(title, self.title_font, info_max_w)

            # Shadow
            for dx, dy in [(-1, 1), (1, 1), (0, 2)]:
                draw.text(
                    (info_x + dx, title_y + dy),
                    title_trimmed,
                    font=self.title_font,
                    fill=(80, 30, 130)
                )
            # Main title
            draw.text(
                (info_x, title_y),
                title_trimmed,
                font=self.title_font,
                fill=(248, 243, 255)
            )

            # ── ACCENT LINE ──
            accent_y = title_y + self.title_font.size + 14
            draw.rounded_rectangle(
                [info_x, accent_y, info_x + 240, accent_y + 2],
                radius=1,
                fill=(140, 70, 240)
            )

            # ── VIEWS ──
            views_y = accent_y + 20
            views = song.view_count or "Unknown"
            draw.text(
                (info_x, views_y),
                f"YouTube  ·  {views}",
                font=self.regular_font,
                fill=(165, 145, 205)
            )

            # ── PROGRESS BAR ──
            bar_x1 = info_x
            bar_x2 = ip_x2 - 45
            bar_y = views_y + 60
            bar_h = 5
            bar_w = bar_x2 - bar_x1
            fill_w = int(bar_w * 0.38)

            # Track
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x2, bar_y + bar_h],
                radius=3,
                fill=(45, 20, 75)
            )
            # Fill
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x1 + fill_w, bar_y + bar_h],
                radius=3,
                fill=(150, 75, 245)
            )
            # Dot
            dot_x = bar_x1 + fill_w
            dot_y = bar_y + bar_h // 2
            # Outer glow dot
            draw.ellipse(
                [dot_x - 9, dot_y - 9, dot_x + 9, dot_y + 9],
                fill=(100, 40, 180)
            )
            # Inner dot
            draw.ellipse(
                [dot_x - 6, dot_y - 6, dot_x + 6, dot_y + 6],
                fill=(200, 155, 255)
            )

            # Time
            time_y = bar_y + bar_h + 12
            draw.text(
                (bar_x1, time_y),
                "00:00",
                font=self.small_font,
                fill=(130, 105, 185)
            )
            duration = getattr(song, 'duration', '00:00')
            dur_w = self.small_font.getlength(duration)
            draw.text(
                (bar_x2 - dur_w, time_y),
                duration,
                font=self.small_font,
                fill=(130, 105, 185)
            )

            # ── REQUESTED BY ──
            req_y = time_y + 42
            requested_by = getattr(song, 'requested_by', None)
            if requested_by:
                name = getattr(
                    requested_by, 'first_name', '') or str(requested_by)

                # Thin separator line
                draw.rounded_rectangle(
                    [info_x, req_y - 14, ip_x2 - 45, req_y - 13],
                    radius=1,
                    fill=(60, 30, 100)
                )

                draw.text(
                    (info_x, req_y),
                    "▸  Requested by",
                    font=self.small_font,
                    fill=(140, 110, 195)
                )
                name_x = info_x + self.small_font.getlength("▸  Requested by  ")
                draw.text(
                    (name_x, req_y),
                    name,
                    font=self.small_font,
                    fill=(210, 180, 255)
                )

            # ─────────────────────────────────────────
            # 4. SAVE
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
