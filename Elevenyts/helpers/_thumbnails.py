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
                "Elevenyts/helpers/Raleway-Bold.ttf", 50)
            self.nowplaying_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 20)
            self.regular_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 22)
            self.small_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 18)
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
        """Paste image with rounded corners."""
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, *img.size), radius, fill=255)
        bg.paste(img, pos, mask)

    def _draw_shadow(self, canvas, x1, y1, x2, y2, radius, shadow_color=(0, 0, 0), intensity=5):
        """Draw soft shadow under a panel."""
        draw = ImageDraw.Draw(canvas)
        for i in range(intensity, 0, -1):
            alpha = int(120 * (i / intensity))
            shadow = (*shadow_color, alpha)
            draw.rounded_rectangle(
                [x1 + i, y1 + i, x2 + i, y2 + i],
                radius=radius,
                fill=shadow
            )

    def _draw_glass_panel(self, canvas, x1, y1, x2, y2, radius=24,
                          fill=(20, 10, 40, 210), border=(255, 255, 255, 25)):
        """Draw a frosted glass panel with border."""
        # Shadow first
        shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        for i in range(18, 0, -1):
            alpha = int(90 * (i / 18))
            shadow_draw.rounded_rectangle(
                [x1 + i, y1 + i, x2 + i, y2 + i],
                radius=radius,
                fill=(0, 0, 0, alpha)
            )
        canvas_comp = Image.alpha_composite(canvas, shadow_layer)
        canvas.paste(canvas_comp, (0, 0))

        # Glass fill
        glass = Image.new("RGBA", (x2 - x1, y2 - y1), fill)
        glass_mask = Image.new("L", glass.size, 0)
        ImageDraw.Draw(glass_mask).rounded_rectangle(
            (0, 0, *glass.size), radius=radius, fill=255)
        glass.putalpha(glass_mask)
        canvas.paste(glass, (x1, y1), glass)

        # Subtle border
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=radius,
            outline=border,
            width=1
        )

        # Top highlight — premium glass feel
        highlight = Image.new("RGBA", (x2 - x1, 3), (255, 255, 255, 40))
        highlight_mask = Image.new("L", highlight.size, 255)
        canvas.paste(highlight, (x1 + radius, y1 + 1), highlight_mask)

    def _generate_sync(self, temp: str, output: str, song: Track, size=(1280, 720)) -> str:
        try:
            W, H = size  # 1280 x 720

            # ─────────────────────────────────────────
            # 1. BACKGROUND — blurred dark
            # ─────────────────────────────────────────
            with Image.open(temp) as raw:
                bg = raw.resize((W, H)).convert("RGBA")

            bg = bg.filter(ImageFilter.GaussianBlur(30))

            # Dark overlay
            overlay = Image.new("RGBA", (W, H), (5, 2, 15, 195))
            bg = Image.alpha_composite(bg, overlay)

            # Subtle dark vignette
            vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vdraw = ImageDraw.Draw(vignette)
            for i in range(80):
                alpha = int(140 * (i / 80))
                vdraw.rectangle(
                    [i, i, W - i, H - i],
                    outline=(0, 0, 0, alpha)
                )
            bg = Image.alpha_composite(bg, vignette)

            # ─────────────────────────────────────────
            # 2. THUMBNAIL GLASS PANEL — left
            # ─────────────────────────────────────────
            thumb_size = 220
            thumb_panel_pad = 20

            tp_x1 = 60
            tp_y1 = (H - thumb_size - thumb_panel_pad * 2) // 2
            tp_x2 = tp_x1 + thumb_size + thumb_panel_pad * 2
            tp_y2 = tp_y1 + thumb_size + thumb_panel_pad * 2

            self._draw_glass_panel(
                bg,
                tp_x1, tp_y1, tp_x2, tp_y2,
                radius=28,
                fill=(18, 8, 38, 220),
                border=(255, 255, 255, 30)
            )

            # Square crop + resize thumbnail
            with Image.open(temp) as raw_thumb:
                cropped = square_crop(raw_thumb.convert("RGBA"))
                thumb = cropped.resize((thumb_size, thumb_size))

            self._paste_rounded(
                bg, thumb,
                (tp_x1 + thumb_panel_pad, tp_y1 + thumb_panel_pad),
                radius=18
            )

            # ─────────────────────────────────────────
            # 3. INFO GLASS PANEL — right
            # ─────────────────────────────────────────
            ip_x1 = tp_x2 + 40
            ip_y1 = tp_y1
            ip_x2 = W - 60
            ip_y2 = tp_y2

            self._draw_glass_panel(
                bg,
                ip_x1, ip_y1, ip_x2, ip_y2,
                radius=28,
                fill=(18, 8, 38, 220),
                border=(255, 255, 255, 30)
            )

            draw = ImageDraw.Draw(bg)
            info_x = ip_x1 + 35
            info_max_w = ip_x2 - info_x - 30
            info_y = ip_y1 + 35

            # ── NOW PLAYING ──
            # Small dot
            dot_x = info_x
            dot_y = info_y + 6
            draw.ellipse(
                [dot_x, dot_y, dot_x + 10, dot_y + 10],
                fill=(180, 80, 255)
            )
            draw.text(
                (info_x + 18, info_y),
                "NOW PLAYING",
                font=self.nowplaying_font,
                fill=(180, 80, 255)
            )

            # ── SONG TITLE ──
            title_y = info_y + 38
            title = re.sub(r"\W+", " ", song.title).title()
            title_trimmed = trim_to_width(
                title, self.title_font, info_max_w)

            # Subtle glow behind title
            for dx, dy in [(-1, 1), (1, 1), (0, 2)]:
                draw.text(
                    (info_x + dx, title_y + dy),
                    title_trimmed,
                    font=self.title_font,
                    fill=(100, 40, 160)
                )
            draw.text(
                (info_x, title_y),
                title_trimmed,
                font=self.title_font,
                fill=(245, 240, 255)
            )

            # ── THIN ACCENT LINE ──
            accent_y = title_y + self.title_font.size + 12
            draw.rounded_rectangle(
                [info_x, accent_y, info_x + 260, accent_y + 2],
                radius=1,
                fill=(160, 80, 255)
            )

            # ── VIEWS ──
            views_y = accent_y + 18
            views = song.view_count or "Unknown"
            draw.text(
                (info_x, views_y),
                f"YouTube  ·  {views}",
                font=self.regular_font,
                fill=(170, 150, 210)
            )

            # ── PROGRESS BAR ──
            bar_x1 = info_x
            bar_x2 = ip_x2 - 35
            bar_y = views_y + 55
            bar_h = 5
            bar_w = bar_x2 - bar_x1
            fill_w = int(bar_w * 0.38)

            # Track bg
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x2, bar_y + bar_h],
                radius=3,
                fill=(50, 25, 80)
            )
            # Filled
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x1 + fill_w, bar_y + bar_h],
                radius=3,
                fill=(160, 80, 255)
            )
            # Dot
            dot_x = bar_x1 + fill_w
            dot_y = bar_y + bar_h // 2
            draw.ellipse(
                [dot_x - 7, dot_y - 7, dot_x + 7, dot_y + 7],
                fill=(200, 140, 255)
            )

            # Time labels
            time_y = bar_y + bar_h + 10
            draw.text(
                (bar_x1, time_y),
                "00:00",
                font=self.small_font,
                fill=(140, 110, 190)
            )
            duration = getattr(song, 'duration', '00:00')
            dur_w = self.small_font.getlength(duration)
            draw.text(
                (bar_x2 - dur_w, time_y),
                duration,
                font=self.small_font,
                fill=(140, 110, 190)
            )

            # ── REQUESTED BY ──
            req_y = time_y + 35
            requested_by = getattr(song, 'requested_by', None)
            if requested_by:
                name = getattr(
                    requested_by, 'first_name', '') or str(requested_by)
                draw.text(
                    (info_x, req_y),
                    "▸",
                    font=self.small_font,
                    fill=(160, 80, 255)
                )
                draw.text(
                    (info_x + 20, req_y),
                    "Requested by",
                    font=self.small_font,
                    fill=(150, 120, 200)
                )
                name_x = info_x + 20 + \
                    self.small_font.getlength("Requested by  ")
                draw.text(
                    (name_x, req_y),
                    name,
                    font=self.small_font,
                    fill=(220, 190, 255)
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
