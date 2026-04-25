# ==============================================================================
# _thumbnails.py - Premium Music Card Thumbnail
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
    w, h = img.size
    min_side = min(w, h)
    left = (w - min_side) // 2
    top = (h - min_side) // 2
    return img.crop((left, top, left + min_side, top + min_side))


class Thumbnail:
    def __init__(self):
        try:
            self.brand_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 24)
            self.title_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 58)
            self.artist_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 32)
            self.time_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 26)
            self.small_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 22)
            self.icon_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 38)
        except OSError:
            self.brand_font = self.title_font = self.artist_font = \
                self.time_font = self.small_font = self.icon_font = ImageFont.load_default()

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

    def _draw_glass_card(self, canvas, x1, y1, x2, y2, radius=40):
        """Premium glass card with shadow, fill, border, highlight."""
        # Multi-layer shadow
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(shadow)
        for i in range(30, 0, -1):
            alpha = int(120 * (i / 30))
            sdraw.rounded_rectangle(
                [x1 + i, y1 + i//2, x2 + i, y2 + i//2],
                radius=radius,
                fill=(0, 0, 0, alpha)
            )
        merged = Image.alpha_composite(canvas, shadow)
        canvas.paste(merged, (0, 0))

        # Glass fill — rich dark purple
        glass = Image.new("RGBA", (x2 - x1, y2 - y1), (16, 6, 36, 235))
        mask = Image.new("L", glass.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, *glass.size), radius=radius, fill=255)
        glass.putalpha(mask)
        canvas.paste(glass, (x1, y1), glass)

        draw = ImageDraw.Draw(canvas)

        # Outer border — subtle white
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=radius,
            outline=(255, 255, 255, 30),
            width=1
        )

        # Inner border — purple accent
        draw.rounded_rectangle(
            [x1 + 2, y1 + 2, x2 - 2, y2 - 2],
            radius=radius - 2,
            outline=(140, 60, 240, 40),
            width=1
        )

        # Top shine highlight
        shine_w = (x2 - x1) - radius * 2
        if shine_w > 0:
            shine = Image.new("RGBA", (shine_w, 3), (255, 255, 255, 45))
            canvas.paste(shine, (x1 + radius, y1 + 3), shine)

        # Bottom subtle glow line
        draw.rounded_rectangle(
            [x1 + 40, y2 - 3, x2 - 40, y2 - 1],
            radius=1,
            fill=(140, 60, 240, 60)
        )

    def _draw_progress_bar(self, draw, x1, y, x2, fill_ratio=0.38):
        """Premium progress bar."""
        bar_h = 6
        fill_w = int((x2 - x1) * fill_ratio)

        # Track bg
        draw.rounded_rectangle(
            [x1, y, x2, y + bar_h],
            radius=3,
            fill=(50, 25, 85)
        )

        # Filled — gradient-like with 2 rects
        draw.rounded_rectangle(
            [x1, y, x1 + fill_w, y + bar_h],
            radius=3,
            fill=(160, 80, 255)
        )
        # Brighter left portion for gradient feel
        draw.rounded_rectangle(
            [x1, y, x1 + fill_w // 2, y + bar_h],
            radius=3,
            fill=(190, 110, 255)
        )

        # Dot
        dot_x = x1 + fill_w
        dot_y = y + bar_h // 2
        # Outer glow
        draw.ellipse(
            [dot_x - 11, dot_y - 11, dot_x + 11, dot_y + 11],
            fill=(100, 40, 180)
        )
        # Mid
        draw.ellipse(
            [dot_x - 8, dot_y - 8, dot_x + 8, dot_y + 8],
            fill=(160, 80, 255)
        )
        # Inner bright
        draw.ellipse(
            [dot_x - 5, dot_y - 5, dot_x + 5, dot_y + 5],
            fill=(220, 170, 255)
        )

    def _draw_volume_bar(self, draw, x1, y, x2, fill_ratio=0.65):
        """Volume bar — thinner."""
        bar_h = 4
        fill_w = int((x2 - x1) * fill_ratio)
        draw.rounded_rectangle(
            [x1, y, x2, y + bar_h],
            radius=2,
            fill=(40, 18, 70)
        )
        draw.rounded_rectangle(
            [x1, y, x1 + fill_w, y + bar_h],
            radius=2,
            fill=(120, 60, 210)
        )

    def _draw_controls(self, draw, cx, y, spacing=110):
        """Draw music control symbols."""
        controls = [
            ("★", (160, 130, 210), 38),   # favourite
            ("⏮", (200, 170, 240), 42),   # prev
            ("⏸", (255, 255, 255), 52),   # pause — bigger, white
            ("⏭", (200, 170, 240), 42),   # next
            ("🎧", (160, 130, 210), 36),  # headphones
        ]
        positions = [
            cx - spacing * 2,
            cx - spacing,
            cx,
            cx + spacing,
            cx + spacing * 2,
        ]
        for (symbol, color, size), x in zip(controls, positions):
            try:
                font = ImageFont.truetype(
                    "Elevenyts/helpers/Raleway-Bold.ttf", size)
            except:
                font = ImageFont.load_default()
            sw = font.getlength(symbol)
            draw.text(
                (x - sw // 2, y),
                symbol,
                font=font,
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

            bg = bg.filter(ImageFilter.GaussianBlur(35))

            # Dark overlay
            overlay = Image.new("RGBA", (W, H), (4, 1, 12, 210))
            bg = Image.alpha_composite(bg, overlay)

            # Purple radial glow
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            for i in range(500, 0, -1):
                alpha = int(30 * (1 - i / 500))
                gd.ellipse(
                    [W // 2 - i, H // 2 - i, W // 2 + i, H // 2 + i],
                    fill=(90, 20, 180, alpha)
                )
            bg = Image.alpha_composite(bg, glow)

            # Vignette
            vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vd = ImageDraw.Draw(vig)
            for i in range(120):
                alpha = int(180 * (i / 120))
                vd.rectangle(
                    [i, i, W - i, H - i],
                    outline=(0, 0, 0, alpha)
                )
            bg = Image.alpha_composite(bg, vig)

            # ─────────────────────────────────────────
            # 2. MAIN GLASS CARD
            # ─────────────────────────────────────────
            card_pad = 60
            cx1 = card_pad
            cy1 = card_pad
            cx2 = W - card_pad
            cy2 = H - card_pad

            self._draw_glass_card(bg, cx1, cy1, cx2, cy2, radius=44)

            draw = ImageDraw.Draw(bg)

            # ─────────────────────────────────────────
            # 3. LEFT — THUMBNAIL
            # ─────────────────────────────────────────
            thumb_size = 340
            thumb_x = cx1 + 44
            thumb_y = cy1 + (cy2 - cy1 - thumb_size) // 2

            # Glow behind thumb
            glow_thumb = Image.new("RGBA", bg.size, (0, 0, 0, 0))
            gt_draw = ImageDraw.Draw(glow_thumb)
            for i in range(25, 0, -1):
                alpha = int(80 * (i / 25))
                gt_draw.rounded_rectangle(
                    [thumb_x - i, thumb_y - i,
                     thumb_x + thumb_size + i, thumb_y + thumb_size + i],
                    radius=28 + i,
                    fill=(130, 50, 240, alpha)
                )
            bg = Image.alpha_composite(bg, glow_thumb)
            draw = ImageDraw.Draw(bg)

            with Image.open(temp) as raw_thumb:
                cropped = square_crop(raw_thumb.convert("RGBA"))
                thumb = cropped.resize((thumb_size, thumb_size))

            self._paste_rounded(bg, thumb, (thumb_x, thumb_y), radius=24)

            # Border around thumb
            draw.rounded_rectangle(
                [thumb_x - 2, thumb_y - 2,
                 thumb_x + thumb_size + 2, thumb_y + thumb_size + 2],
                radius=26,
                outline=(160, 80, 255, 180),
                width=2
            )

            # ─────────────────────────────────────────
            # 4. RIGHT — INFO
            # ─────────────────────────────────────────
            info_x = thumb_x + thumb_size + 55
            info_max_w = cx2 - info_x - 44

            # ── BRAND NAME ──
            brand_y = cy1 + 44
            draw.text(
                (info_x, brand_y),
                "Galaxy Bots",
                font=self.brand_font,
                fill=(140, 100, 210)
            )

            # ── SONG TITLE ──
            title_y = brand_y + 48
            title = re.sub(r"\W+", " ", song.title).title()
            title_trimmed = trim_to_width(title, self.title_font, info_max_w)

            # Shadow
            for dx, dy in [(-2, 2), (2, 2), (0, 3)]:
                draw.text(
                    (info_x + dx, title_y + dy),
                    title_trimmed,
                    font=self.title_font,
                    fill=(70, 25, 120)
                )
            draw.text(
                (info_x, title_y),
                title_trimmed,
                font=self.title_font,
                fill=(252, 248, 255)
            )

            # ── ARTIST / REQUESTED BY ──
            artist_y = title_y + self.title_font.size + 16
            requested_by = getattr(song, 'requested_by', None)
            if requested_by:
                name = getattr(
                    requested_by, 'first_name', '') or str(requested_by)
            else:
                name = "YouTube"

            draw.text(
                (info_x, artist_y),
                name,
                font=self.artist_font,
                fill=(180, 150, 230)
            )

            # ── ACCENT LINE ──
            accent_y = artist_y + self.artist_font.size + 20
            draw.rounded_rectangle(
                [info_x, accent_y, info_x + 280, accent_y + 2],
                radius=1,
                fill=(140, 70, 240)
            )

            # ── PROGRESS BAR + TIME ──
            bar_x1 = info_x
            bar_x2 = cx2 - 44
            bar_y = accent_y + 28

            # Time left
            draw.text(
                (bar_x1, bar_y),
                "0:24",
                font=self.time_font,
                fill=(160, 130, 210)
            )

            duration = getattr(song, 'duration', '0:00')
            dur_label = f"−{duration}"
            dur_w = self.time_font.getlength(dur_label)
            draw.text(
                (bar_x2 - dur_w, bar_y),
                dur_label,
                font=self.time_font,
                fill=(160, 130, 210)
            )

            # Bar below time
            pb_y = bar_y + self.time_font.size + 14
            time_offset = self.time_font.getlength("0:24") + 20
            self._draw_progress_bar(
                draw,
                bar_x1 + time_offset, pb_y,
                bar_x2 - int(dur_w) - 20
            )

            # ── CONTROLS ──
            controls_y = pb_y + 55
            ctrl_cx = (info_x + cx2 - 44) // 2
            self._draw_controls(draw, ctrl_cx, controls_y, spacing=105)

            # ── VOLUME BAR ──
            vol_y = controls_y + 80
            # Volume icon left
            draw.text(
                (bar_x1, vol_y - 2),
                "◁",
                font=self.small_font,
                fill=(130, 100, 190)
            )
            # Volume icon right
            draw.text(
                (bar_x2 - 20, vol_y - 2),
                "◁))",
                font=self.small_font,
                fill=(130, 100, 190)
            )
            vol_x1 = bar_x1 + 30
            vol_x2 = bar_x2 - 40
            self._draw_volume_bar(draw, vol_x1, vol_y + 4, vol_x2)

            # ─────────────────────────────────────────
            # 5. SAVE
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
