# ==============================================================================
# _thumbnails.py - Premium Thumbnail Generator (Full Detailed)
# ==============================================================================

import os
import re
import math
import asyncio
import aiohttp
import random
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
            self.title_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 52)
            self.nowplaying_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 22)
            self.regular_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 24)
            self.small_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 20)
            self.badge_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 18)
        except OSError:
            self.title_font = self.nowplaying_font = self.regular_font = \
                self.small_font = self.badge_font = ImageFont.load_default()

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

    def _draw_badge(self, draw, x, y, text, bg_color, text_color, font, pad_x=14, pad_y=6, radius=10):
        """Draw a small rounded badge."""
        tw = font.getlength(text)
        bx1, by1 = x, y
        bx2 = x + tw + pad_x * 2
        by2 = y + font.size + pad_y * 2
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=radius, fill=bg_color)
        draw.text((bx1 + pad_x, by1 + pad_y), text, font=font, fill=text_color)
        return bx2  # return end x for chaining badges

    def _draw_waveform(self, draw, x, y, width, height, color, bar_count=40):
        """Draw a decorative static waveform."""
        bar_w = 4
        gap = (width - bar_w * bar_count) // (bar_count - 1) if bar_count > 1 else 0
        seed_vals = [
            0.4, 0.6, 0.8, 1.0, 0.9, 0.7, 0.5, 0.8, 1.0, 0.6,
            0.3, 0.5, 0.9, 1.0, 0.8, 0.6, 0.4, 0.7, 1.0, 0.9,
            0.5, 0.3, 0.6, 0.8, 1.0, 0.7, 0.5, 0.9, 0.8, 0.6,
            0.4, 0.7, 1.0, 0.8, 0.5, 0.3, 0.6, 0.9, 0.7, 0.5,
        ]
        for i in range(bar_count):
            h_ratio = seed_vals[i % len(seed_vals)]
            bar_h = int(height * h_ratio)
            bx = x + i * (bar_w + gap)
            by_center = y + height // 2
            r, g, b, a = color
            # Bars above and below center (mirror effect)
            draw.rounded_rectangle(
                [bx, by_center - bar_h // 2,
                 bx + bar_w, by_center + bar_h // 2],
                radius=2,
                fill=(r, g, b, a)
            )

    def _draw_dot_grid(self, canvas, x1, y1, x2, y2, color=(255, 255, 255, 10)):
        """Draw subtle dot grid pattern."""
        draw = ImageDraw.Draw(canvas)
        spacing = 22
        for row_y in range(y1 + 11, y2, spacing):
            for col_x in range(x1 + 11, x2, spacing):
                draw.ellipse(
                    [col_x - 1, row_y - 1, col_x + 1, row_y + 1],
                    fill=color
                )

    def _generate_sync(self, temp: str, output: str, song: Track, size=(1280, 720)) -> str:
        try:
            W, H = size

            # ─────────────────────────────────────────
            # 1. BACKGROUND
            # ─────────────────────────────────────────
            with Image.open(temp) as raw:
                bg = raw.resize((W, H)).convert("RGBA")

            bg = bg.filter(ImageFilter.GaussianBlur(30))

            overlay = Image.new("RGBA", (W, H), (5, 2, 15, 200))
            bg = Image.alpha_composite(bg, overlay)

            # Radial glow center
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow)
            for i in range(400, 0, -1):
                alpha = int(35 * (1 - i / 400))
                glow_draw.ellipse(
                    [W // 2 - i, H // 2 - i, W // 2 + i, H // 2 + i],
                    fill=(80, 20, 160, alpha)
                )
            bg = Image.alpha_composite(bg, glow)

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
            # 2. THUMBNAIL PANEL — left full height
            # ─────────────────────────────────────────
            tp_x1, tp_y1 = 40, 40
            tp_x2, tp_y2 = 360, H - 40

            # Dot grid on thumb panel
            self._draw_dot_grid(bg, tp_x1, tp_y1, tp_x2, tp_y2)

            self._draw_glass_panel(
                bg, tp_x1, tp_y1, tp_x2, tp_y2,
                radius=28,
                fill=(15, 6, 32, 225),
                border=(255, 255, 255, 28)
            )

            # Square crop thumbnail
            with Image.open(temp) as raw_thumb:
                cropped = square_crop(raw_thumb.convert("RGBA"))
                thumb_size = tp_x2 - tp_x1 - 40
                thumb = cropped.resize((thumb_size, thumb_size))

            thumb_x = tp_x1 + 20
            thumb_y = tp_y1 + 24
            self._paste_rounded(bg, thumb, (thumb_x, thumb_y), radius=20)

            draw = ImageDraw.Draw(bg)

            # ── DURATION BADGE below thumb ──
            duration = getattr(song, 'duration', '00:00')
            badge_y = thumb_y + thumb_size + 16
            badge_cx = tp_x1 + (tp_x2 - tp_x1) // 2
            dur_w = self.badge_font.getlength(duration) + 28
            self._draw_badge(
                draw,
                badge_cx - int(dur_w // 2), badge_y,
                duration,
                bg_color=(50, 20, 90),
                text_color=(200, 160, 255),
                font=self.badge_font
            )

            # ── HD BADGE ──
            hd_x = self._draw_badge(
                draw,
                tp_x1 + 16, badge_y + 38,
                "HD",
                bg_color=(140, 60, 240),
                text_color=(255, 255, 255),
                font=self.badge_font
            )

            # ── YOUTUBE BADGE ──
            self._draw_badge(
                draw,
                hd_x + 10, badge_y + 38,
                "YouTube",
                bg_color=(30, 12, 60),
                text_color=(170, 130, 220),
                font=self.badge_font
            )

            # ─────────────────────────────────────────
            # 3. INFO PANEL — right full height
            # ─────────────────────────────────────────
            ip_x1 = tp_x2 + 30
            ip_y1 = 40
            ip_x2 = W - 40
            ip_y2 = H - 40

            # Dot grid on info panel
            self._draw_dot_grid(bg, ip_x1, ip_y1, ip_x2, ip_y2)

            self._draw_glass_panel(
                bg, ip_x1, ip_y1, ip_x2, ip_y2,
                radius=28,
                fill=(15, 6, 32, 225),
                border=(255, 255, 255, 28)
            )

            draw = ImageDraw.Draw(bg)
            info_x = ip_x1 + 45
            info_max_w = ip_x2 - info_x - 35

            # ── NOW PLAYING ──
            np_y = ip_y1 + 38
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
            title_y = np_y + 48
            title = re.sub(r"\W+", " ", song.title).title()
            title_trimmed = trim_to_width(title, self.title_font, info_max_w)

            for dx, dy in [(-1, 1), (1, 1), (0, 2)]:
                draw.text(
                    (info_x + dx, title_y + dy),
                    title_trimmed,
                    font=self.title_font,
                    fill=(80, 30, 130)
                )
            draw.text(
                (info_x, title_y),
                title_trimmed,
                font=self.title_font,
                fill=(248, 243, 255)
            )

            # ── ACCENT LINE ──
            accent_y = title_y + self.title_font.size + 14
            draw.rounded_rectangle(
                [info_x, accent_y, info_x + 260, accent_y + 2],
                radius=1,
                fill=(140, 70, 240)
            )

            # ── STATS ROW ──
            stats_y = accent_y + 18
            views = song.view_count or "Unknown"
            stats_items = [
                (f"👁  {views}", (165, 145, 205)),
                (f"⏱  {duration}", (165, 145, 205)),
            ]
            sx = info_x
            for stat_text, stat_color in stats_items:
                draw.text((sx, stats_y), stat_text,
                         font=self.regular_font, fill=stat_color)
                sx += self.regular_font.getlength(stat_text) + 30

            # ── WAVEFORM ──
            wave_y = stats_y + 52
            wave_h = 55
            wave_w = ip_x2 - info_x - 35
            self._draw_waveform(
                draw,
                info_x, wave_y,
                wave_w, wave_h,
                color=(140, 70, 220, 130),
                bar_count=52
            )

            # ── PROGRESS BAR ──
            bar_x1 = info_x
            bar_x2 = ip_x2 - 45
            bar_y = wave_y + wave_h + 20
            bar_h = 5
            bar_w = bar_x2 - bar_x1
            fill_w = int(bar_w * 0.38)

            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x2, bar_y + bar_h],
                radius=3,
                fill=(45, 20, 75)
            )
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x1 + fill_w, bar_y + bar_h],
                radius=3,
                fill=(150, 75, 245)
            )
            dot_x = bar_x1 + fill_w
            dot_y = bar_y + bar_h // 2
            draw.ellipse(
                [dot_x - 9, dot_y - 9, dot_x + 9, dot_y + 9],
                fill=(100, 40, 180)
            )
            draw.ellipse(
                [dot_x - 6, dot_y - 6, dot_x + 6, dot_y + 6],
                fill=(200, 155, 255)
            )

            # Time
            time_y = bar_y + bar_h + 12
            draw.text(
                (bar_x1, time_y), "00:00",
                font=self.small_font, fill=(130, 105, 185)
            )
            dur_w_px = self.small_font.getlength(duration)
            draw.text(
                (bar_x2 - dur_w_px, time_y), duration,
                font=self.small_font, fill=(130, 105, 185)
            )

            # ── SEPARATOR ──
            sep_y = time_y + 30
            draw.rounded_rectangle(
                [info_x, sep_y, ip_x2 - 45, sep_y + 1],
                radius=1,
                fill=(55, 28, 95)
            )

            # ── REQUESTED BY ──
            req_y = sep_y + 18
            requested_by = getattr(song, 'requested_by', None)
            if requested_by:
                name = getattr(
                    requested_by, 'first_name', '') or str(requested_by)
                draw.text(
                    (info_x, req_y), "▸  Requested by",
                    font=self.small_font, fill=(140, 110, 195)
                )
                name_x = info_x + self.small_font.getlength("▸  Requested by  ")
                draw.text(
                    (name_x, req_y), name,
                    font=self.small_font, fill=(210, 180, 255)
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
