# ==============================================================================
# _thumbnails.py - Circle 3D Overflow Premium Thumbnail
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
                "Elevenyts/helpers/Raleway-Bold.ttf", 56)
            self.title_font_sm = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 44)
            self.artist_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 30)
            self.time_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 24)
            self.small_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 20)
            self.ctrl_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 40)
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
        size = radius * 2
        img_resized = img.resize((size, size))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        x = center[0] - radius
        y = center[1] - radius
        bg.paste(img_resized, (x, y), mask)

    def _draw_glass_box(self, canvas, x1, y1, x2, y2, radius=36):
        # Multi layer shadow
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        for i in range(28, 0, -1):
            alpha = int(130 * (i / 28))
            sd.rounded_rectangle(
                [x1 + i, y1 + i // 2, x2 + i, y2 + i // 2],
                radius=radius, fill=(0, 0, 0, alpha)
            )
        merged = Image.alpha_composite(canvas, shadow)
        canvas.paste(merged, (0, 0))

        # Glass fill
        glass = Image.new("RGBA", (x2 - x1, y2 - y1), (14, 5, 30, 235))
        mask = Image.new("L", glass.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, *glass.size), radius=radius, fill=255)
        glass.putalpha(mask)
        canvas.paste(glass, (x1, y1), glass)

        draw = ImageDraw.Draw(canvas)
        # Outer border
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=radius,
            outline=(255, 255, 255, 28),
            width=1
        )
        # Purple inner border
        draw.rounded_rectangle(
            [x1 + 2, y1 + 2, x2 - 2, y2 - 2],
            radius=radius - 2,
            outline=(140, 60, 240, 40),
            width=1
        )
        # Top shine
        hl_w = x2 - x1 - radius * 2
        if hl_w > 0:
            shine = Image.new("RGBA", (hl_w, 2), (255, 255, 255, 42))
            canvas.paste(shine, (x1 + radius, y1 + 3), shine)
        # Bottom glow
        draw.rounded_rectangle(
            [x1 + 50, y2 - 3, x2 - 50, y2 - 1],
            radius=1, fill=(140, 60, 240, 55)
        )

    def _draw_progress_bar(self, draw, x1, y, x2, fill_ratio=0.38):
        bar_h = 6
        fill_w = int((x2 - x1) * fill_ratio)
        draw.rounded_rectangle(
            [x1, y, x2, y + bar_h], radius=3, fill=(50, 25, 85))
        draw.rounded_rectangle(
            [x1, y, x1 + fill_w, y + bar_h], radius=3, fill=(180, 100, 255))
        draw.rounded_rectangle(
            [x1, y, x1 + fill_w // 2, y + bar_h], radius=3, fill=(210, 140, 255))
        dot_x = x1 + fill_w
        dot_y = y + bar_h // 2
        draw.ellipse(
            [dot_x - 10, dot_y - 10, dot_x + 10, dot_y + 10], fill=(100, 40, 180))
        draw.ellipse(
            [dot_x - 7, dot_y - 7, dot_x + 7, dot_y + 7], fill=(180, 100, 255))
        draw.ellipse(
            [dot_x - 4, dot_y - 4, dot_x + 4, dot_y + 4], fill=(230, 180, 255))

    def _wrap_title(self, title, font, max_w):
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
        if current:
            lines.append(current)
        return lines[:2]

    def _generate_sync(self, temp, output, song, size=(1280, 720)):
        try:
            W, H = size

            # ── BACKGROUND ──
            with Image.open(temp) as raw:
                bg = raw.resize((W, H)).convert("RGBA")
            bg = bg.filter(ImageFilter.GaussianBlur(28))

            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 125))
            bg = Image.alpha_composite(bg, overlay)

            vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vd = ImageDraw.Draw(vig)
            for i in range(120):
                alpha = int(200 * (i / 120))
                vd.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, alpha))
            bg = Image.alpha_composite(bg, vig)

            # ── CIRCLE DIMENSIONS ──
            circle_r = 240
            circle_cx = 280          # Left side — overflow left of box
            circle_cy = H // 2

            # ── GLASS BOX — starts after circle center ──
            bx1 = circle_cx - 20     # Box starts slightly before circle center
            by1 = 45
            bx2 = W - 45
            by2 = H - 45

            self._draw_glass_box(bg, bx1, by1, bx2, by2, radius=38)

            # ── 3D SHADOW UNDER CIRCLE ──
            shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow_layer)
            for i in range(35, 0, -1):
                alpha = int(100 * (i / 35))
                sd.ellipse(
                    [circle_cx - circle_r - i + 15,
                     circle_cy - circle_r - i + 15,
                     circle_cx + circle_r + i + 15,
                     circle_cy + circle_r + i + 15],
                    fill=(0, 0, 0, alpha)
                )
            bg = Image.alpha_composite(bg, shadow_layer)

            draw = ImageDraw.Draw(bg)

            # ── GLOW RINGS ──
            for i in range(30, 0, -5):
                alpha = int(60 * (i / 30))
                draw.ellipse(
                    [circle_cx - circle_r - i, circle_cy - circle_r - i,
                     circle_cx + circle_r + i, circle_cy + circle_r + i],
                    outline=(160, 80, 255, alpha), width=2
                )

            # ── OUTER BORDER — thick purple ──
            draw.ellipse(
                [circle_cx - circle_r - 14, circle_cy - circle_r - 14,
                 circle_cx + circle_r + 14, circle_cy + circle_r + 14],
                outline=(120, 50, 220), width=14
            )
            # Mid border
            draw.ellipse(
                [circle_cx - circle_r - 5, circle_cy - circle_r - 5,
                 circle_cx + circle_r + 5, circle_cy + circle_r + 5],
                outline=(180, 110, 255), width=4
            )
            # Inner bright border
            draw.ellipse(
                [circle_cx - circle_r, circle_cy - circle_r,
                 circle_cx + circle_r, circle_cy + circle_r],
                outline=(220, 170, 255), width=2
            )

            # ── PASTE CIRCLE THUMB ──
            with Image.open(temp) as raw_thumb:
                cropped = square_crop(raw_thumb.convert("RGBA"))
            self._paste_circle(bg, cropped, (circle_cx, circle_cy), circle_r)

            # Redraw borders on top of thumb
            draw = ImageDraw.Draw(bg)
            draw.ellipse(
                [circle_cx - circle_r - 5, circle_cy - circle_r - 5,
                 circle_cx + circle_r + 5, circle_cy + circle_r + 5],
                outline=(180, 110, 255), width=4
            )
            draw.ellipse(
                [circle_cx - circle_r, circle_cy - circle_r,
                 circle_cx + circle_r, circle_cy + circle_r],
                outline=(220, 170, 255), width=2
            )

            # ── GALAXY BOTS — top right ──
            brand = "Galaxy Bots"
            bw = self.brand_font.getlength(brand)
            draw.text(
                (bx2 - bw - 30, by1 + 22),
                brand, font=self.brand_font, fill=(160, 100, 230)
            )

            # ── RIGHT SIDE INFO ──
            info_x = circle_cx + circle_r // 2 + 60
            info_max_w = bx2 - info_x - 40

            # Vertical center calculation
            line_h = self.title_font_sm.size + 8
            total_h = (
                line_h * 2 +
                14 +
                self.artist_font.size +
                26 +
                6 +
                12 +
                self.time_font.size +
                26 +
                self.ctrl_font.size + 16
            )
            start_y = by1 + ((by2 - by1) - total_h) // 2

            # ── TITLE ──
            title_raw = re.sub(r"\W+", " ", song.title).title()
            lines = self._wrap_title(title_raw, self.title_font_sm, info_max_w)
            title_y = start_y

            for i, line in enumerate(lines):
                ly = title_y + i * line_h
                for dx, dy in [(-2, 2), (2, 2)]:
                    draw.text(
                        (info_x + dx, ly + dy), line,
                        font=self.title_font_sm, fill=(55, 18, 100)
                    )
                draw.text(
                    (info_x, ly), line,
                    font=self.title_font_sm, fill=(255, 255, 255)
                )

            title_end_y = title_y + len(lines) * line_h

            # ── ARTIST | VIEWS ──
            artist_y = title_end_y + 14
            requested_by = getattr(song, 'requested_by', None)
            artist_name = (
                getattr(requested_by, 'first_name', '') or str(requested_by)
            ) if requested_by else "YouTube"
            views = song.view_count or "Unknown"
            av_text = trim_to_width(
                f"{artist_name}  |  {views}", self.artist_font, info_max_w)
            draw.text(
                (info_x, artist_y), av_text,
                font=self.artist_font, fill=(200, 175, 240)
            )

            # ── ACCENT LINE ──
            acc_y = artist_y + self.artist_font.size + 12
            draw.rounded_rectangle(
                [info_x, acc_y, info_x + 240, acc_y + 2],
                radius=1, fill=(140, 70, 240)
            )

            # ── PROGRESS BAR ──
            bar_y = acc_y + 18
            bar_x1 = info_x
            bar_x2 = bx2 - 40
            self._draw_progress_bar(draw, bar_x1, bar_y, bar_x2)

            # ── TIME ──
            time_y = bar_y + 6 + 12
            draw.text(
                (bar_x1, time_y), "00:00",
                font=self.time_font, fill=(190, 165, 230)
            )
            duration = getattr(song, 'duration', '0:00')
            dur_w = self.time_font.getlength(duration)
            draw.text(
                (bar_x2 - dur_w, time_y), duration,
                font=self.time_font, fill=(190, 165, 230)
            )

            # ── CONTROLS ──
            ctrl_y = time_y + self.time_font.size + 26
            ctrl_cx = (info_x + bar_x2) // 2
            spacing = (bar_x2 - info_x) // 5

            controls = [
                ("⇄", (170, 140, 220)),
                ("⏮", (195, 165, 235)),
                ("▶", (255, 255, 255)),
                ("⏭", (195, 165, 235)),
                ("↺", (170, 140, 220)),
            ]
            positions = [
                ctrl_cx - spacing * 2,
                ctrl_cx - spacing,
                ctrl_cx,
                ctrl_cx + spacing,
                ctrl_cx + spacing * 2,
            ]

            for (symbol, color), x in zip(controls, positions):
                if symbol == "▶":
                    r = self.ctrl_font.size // 2 + 12
                    draw.ellipse(
                        [x - r, ctrl_y - 8,
                         x + r, ctrl_y + self.ctrl_font.size + 8],
                        fill=(120, 50, 215)
                    )
                    draw.ellipse(
                        [x - r + 4, ctrl_y - 4,
                         x + r - 4, ctrl_y + self.ctrl_font.size + 4],
                        fill=(150, 70, 245)
                    )
                sw = int(self.ctrl_font.getlength(symbol))
                draw.text(
                    (x - sw // 2, ctrl_y),
                    symbol, font=self.ctrl_font, fill=color
                )

            # ── SAVE ──
            final = bg.convert("RGB")
            final.save(output, quality=95)
            try:
                os.remove(temp)
            except:
                pass
            return output

        except Exception:
            return config.DEFAULT_THUMB
