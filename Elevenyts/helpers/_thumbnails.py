# ==============================================================================
# _thumbnails.py - Circle Layout Premium Thumbnail
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
                "Elevenyts/helpers/Raleway-Bold.ttf", 26)
            self.title_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 62)
            self.title_font_sm = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 50)
            self.artist_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 34)
            self.time_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 28)
            self.small_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 22)
            self.ctrl_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 44)
        except OSError:
            self.brand_font = self.title_font = self.title_font_sm = \
                self.artist_font = self.time_font = self.small_font = \
                self.ctrl_font = ImageFont.load_default()

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

    def _paste_circle(self, bg, img, center, radius):
        """Paste image as circle."""
        size = radius * 2
        img_resized = img.resize((size, size))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        x = center[0] - radius
        y = center[1] - radius
        bg.paste(img_resized, (x, y), mask)

    def _draw_circle_border(self, draw, center, radius, color, width=8):
        """Draw colored circle border."""
        cx, cy = center
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=color,
            width=width
        )

    def _draw_progress_bar(self, draw, x1, y, x2, fill_ratio=0.38):
        bar_h = 7
        fill_w = int((x2 - x1) * fill_ratio)

        # Track
        draw.rounded_rectangle(
            [x1, y, x2, y + bar_h],
            radius=4,
            fill=(255, 255, 255, 40)
        )
        # Fill
        draw.rounded_rectangle(
            [x1, y, x1 + fill_w, y + bar_h],
            radius=4,
            fill=(180, 100, 255)
        )
        # Bright left
        draw.rounded_rectangle(
            [x1, y, x1 + fill_w // 2, y + bar_h],
            radius=4,
            fill=(210, 140, 255)
        )
        # Dot
        dot_x = x1 + fill_w
        dot_y = y + bar_h // 2
        draw.ellipse(
            [dot_x - 12, dot_y - 12, dot_x + 12, dot_y + 12],
            fill=(100, 40, 180)
        )
        draw.ellipse(
            [dot_x - 8, dot_y - 8, dot_x + 8, dot_y + 8],
            fill=(190, 110, 255)
        )
        draw.ellipse(
            [dot_x - 4, dot_y - 4, dot_x + 4, dot_y + 4],
            fill=(230, 180, 255)
        )

    def _wrap_title(self, title, font, max_w):
        """Wrap title into max 2 lines."""
        words = title.split()
        lines = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if font.getlength(test) <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
            if len(lines) == 1:
                # Check if rest fits
                pass
        if current:
            lines.append(current)
        return lines[:2]  # Max 2 lines

    def _generate_sync(self, temp, output, song, size=(1280, 720)):
        try:
            W, H = size

            # ─────────────────────────────────────────
            # 1. BACKGROUND
            # ─────────────────────────────────────────
            with Image.open(temp) as raw:
                bg = raw.resize((W, H)).convert("RGBA")

            bg = bg.filter(ImageFilter.GaussianBlur(28))

            # Dark overlay — not too dark, keep BG visible
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 130))
            bg = Image.alpha_composite(bg, overlay)

            # Vignette edges
            vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vd = ImageDraw.Draw(vig)
            for i in range(120):
                alpha = int(200 * (i / 120))
                vd.rectangle(
                    [i, i, W - i, H - i],
                    outline=(0, 0, 0, alpha)
                )
            bg = Image.alpha_composite(bg, vig)

            draw = ImageDraw.Draw(bg)

            # ─────────────────────────────────────────
            # 2. CIRCLE THUMBNAIL — left center
            # ─────────────────────────────────────────
            circle_r = 240
            circle_cx = 320
            circle_cy = H // 2

            # Outer glow rings
            for i in range(30, 0, -5):
                alpha = int(60 * (i / 30))
                draw.ellipse(
                    [circle_cx - circle_r - i,
                     circle_cy - circle_r - i,
                     circle_cx + circle_r + i,
                     circle_cy + circle_r + i],
                    outline=(160, 80, 255, alpha),
                    width=2
                )

            # Outer thick border — purple gradient feel
            draw.ellipse(
                [circle_cx - circle_r - 12,
                 circle_cy - circle_r - 12,
                 circle_cx + circle_r + 12,
                 circle_cy + circle_r + 12],
                outline=(140, 60, 240),
                width=10
            )
            # Inner border — lighter purple
            draw.ellipse(
                [circle_cx - circle_r - 4,
                 circle_cy - circle_r - 4,
                 circle_cx + circle_r + 4,
                 circle_cy + circle_r + 4],
                outline=(200, 140, 255),
                width=3
            )

            # Paste circle thumbnail
            with Image.open(temp) as raw_thumb:
                cropped = square_crop(raw_thumb.convert("RGBA"))
            self._paste_circle(bg, cropped, (circle_cx, circle_cy), circle_r)

            # Re-draw inner border on top of thumb
            draw = ImageDraw.Draw(bg)
            draw.ellipse(
                [circle_cx - circle_r,
                 circle_cy - circle_r,
                 circle_cx + circle_r,
                 circle_cy + circle_r],
                outline=(200, 140, 255),
                width=3
            )

            # ─────────────────────────────────────────
            # 3. RIGHT SIDE INFO
            # ─────────────────────────────────────────
            info_x = circle_cx + circle_r + 80
            info_max_w = W - info_x - 60

            # ── GALAXY BOTS brand — top right ──
            brand_text = "Galaxy Bots"
            brand_w = self.brand_font.getlength(brand_text)
            draw.text(
                (W - brand_w - 50, 36),
                brand_text,
                font=self.brand_font,
                fill=(160, 100, 230)
            )

            # ── SONG TITLE — 2 lines ──
            title_raw = re.sub(r"\W+", " ", song.title).title()
            lines = self._wrap_title(title_raw, self.title_font, info_max_w)

            title_y = H // 2 - 220

            if len(lines) == 1:
                # Single line — use bigger font
                for dx, dy in [(-2, 2), (2, 2)]:
                    draw.text(
                        (info_x + dx, title_y + dy),
                        lines[0],
                        font=self.title_font,
                        fill=(60, 20, 110)
                    )
                draw.text(
                    (info_x, title_y),
                    lines[0],
                    font=self.title_font,
                    fill=(255, 255, 255)
                )
                title_end_y = title_y + self.title_font.size + 10
            else:
                # 2 lines
                for i, line in enumerate(lines):
                    ly = title_y + i * (self.title_font_sm.size + 8)
                    for dx, dy in [(-2, 2), (2, 2)]:
                        draw.text(
                            (info_x + dx, ly + dy),
                            line,
                            font=self.title_font_sm,
                            fill=(60, 20, 110)
                        )
                    draw.text(
                        (info_x, ly),
                        line,
                        font=self.title_font_sm,
                        fill=(255, 255, 255)
                    )
                title_end_y = title_y + \
                    len(lines) * (self.title_font_sm.size + 8) + 10

            # ── ARTIST | VIEWS ──
            artist_y = title_end_y + 18
            requested_by = getattr(song, 'requested_by', None)
            if requested_by:
                artist_name = getattr(
                    requested_by, 'first_name', '') or str(requested_by)
            else:
                artist_name = "YouTube"

            views = song.view_count or "Unknown"
            artist_views = f"{artist_name}  |  {views}"
            artist_views = trim_to_width(
                artist_views, self.artist_font, info_max_w)

            draw.text(
                (info_x, artist_y),
                artist_views,
                font=self.artist_font,
                fill=(210, 185, 245)
            )

            # ── PROGRESS BAR ──
            bar_y = artist_y + self.artist_font.size + 32
            bar_x1 = info_x
            bar_x2 = W - 60
            self._draw_progress_bar(draw, bar_x1, bar_y, bar_x2)

            # ── TIME LABELS ──
            time_y = bar_y + 22
            draw.text(
                (bar_x1, time_y),
                "00:00",
                font=self.time_font,
                fill=(200, 180, 235)
            )
            duration = getattr(song, 'duration', '0:00')
            dur_w = self.time_font.getlength(duration)
            draw.text(
                (bar_x2 - dur_w, time_y),
                duration,
                font=self.time_font,
                fill=(200, 180, 235)
            )

            # ── CONTROLS ──
            controls_y = time_y + self.time_font.size + 32
            ctrl_cx = (info_x + bar_x2) // 2
            spacing = 120

            controls = [
                ("⇄", (180, 150, 225)),   # shuffle
                ("⏮", (200, 170, 240)),   # prev
                ("▶", (255, 255, 255)),   # play — big white
                ("⏭", (200, 170, 240)),   # next
                ("↺", (180, 150, 225)),   # repeat
            ]
            positions = [
                ctrl_cx - spacing * 2,
                ctrl_cx - spacing,
                ctrl_cx,
                ctrl_cx + spacing,
                ctrl_cx + spacing * 2,
            ]

            for (symbol, color), x in zip(controls, positions):
                # Play button special — circle bg
                if symbol == "▶":
                    draw.ellipse(
                        [x - 36, controls_y - 8,
                         x + 36, controls_y + self.ctrl_font.size + 8],
                        fill=(140, 60, 240)
                    )
                    draw.ellipse(
                        [x - 34, controls_y - 6,
                         x + 34, controls_y + self.ctrl_font.size + 6],
                        fill=(160, 80, 255)
                    )
                sw = self.ctrl_font.getlength(symbol)
                draw.text(
                    (x - int(sw // 2), controls_y),
                    symbol,
                    font=self.ctrl_font,
                    fill=color
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
