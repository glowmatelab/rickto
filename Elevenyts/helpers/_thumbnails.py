# ==============================================================================
# _thumbnails.py - Spotify Style 16:9 Music Player Thumbnail
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
            self.title_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 58)
            self.title_font_sm = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 44)
            self.nowplaying_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 22)
            self.meta_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 26)
            self.time_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 22)
            self.small_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 20)
            self.ctrl_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 38)
        except OSError:
            self.title_font = self.title_font_sm = self.nowplaying_font = \
                self.meta_font = self.time_font = self.small_font = \
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

    def _paste_rounded(self, bg, img, pos, radius):
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, *img.size), radius, fill=255)
        bg.paste(img, pos, mask)

    def _draw_glass_card(self, canvas, x1, y1, x2, y2, radius=36):
        # Shadow
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        for i in range(25, 0, -1):
            alpha = int(110 * (i / 25))
            sd.rounded_rectangle(
                [x1 + i, y1 + i // 2, x2 + i, y2 + i // 2],
                radius=radius, fill=(0, 0, 0, alpha)
            )
        merged = Image.alpha_composite(canvas, shadow)
        canvas.paste(merged, (0, 0))

        # Glass fill
        glass = Image.new("RGBA", (x2 - x1, y2 - y1), (18, 8, 38, 215))
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
        # Inner border
        draw.rounded_rectangle(
            [x1 + 2, y1 + 2, x2 - 2, y2 - 2],
            radius=radius - 2,
            outline=(150, 80, 255, 22),
            width=1
        )
        # Top shine
        hl_w = x2 - x1 - radius * 2
        if hl_w > 0:
            shine = Image.new("RGBA", (hl_w, 2), (255, 255, 255, 38))
            canvas.paste(shine, (x1 + radius, y1 + 3), shine)

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

            bg = bg.filter(ImageFilter.GaussianBlur(32))

            overlay = Image.new("RGBA", (W, H), (5, 2, 15, 190))
            bg = Image.alpha_composite(bg, overlay)

            # Radial glow
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            for i in range(400, 0, -1):
                alpha = int(28 * (1 - i / 400))
                gd.ellipse(
                    [W // 2 - i, H // 2 - i, W // 2 + i, H // 2 + i],
                    fill=(80, 20, 160, alpha)
                )
            bg = Image.alpha_composite(bg, glow)

            # Vignette
            vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vd = ImageDraw.Draw(vig)
            for i in range(100):
                alpha = int(180 * (i / 100))
                vd.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, alpha))
            bg = Image.alpha_composite(bg, vig)

            # ── GLASS CARD — wide 16:9 ──
            pad = 45
            cx1, cy1 = pad, pad
            cx2, cy2 = W - pad, H - pad

            self._draw_glass_card(bg, cx1, cy1, cx2, cy2, radius=36)

            draw = ImageDraw.Draw(bg)

            # ── NOW PLAYING — top center ──
            np_y = cy1 + 28
            np_text = "NOW PLAYING"
            np_w = self.nowplaying_font.getlength(np_text)
            np_x = cx1 + (cx2 - cx1 - np_w) // 2 + 14

            # Green dot
            draw.ellipse(
                [np_x - 18, np_y + 5, np_x - 6, np_y + 17],
                fill=(29, 185, 84)
            )
            draw.text(
                (np_x, np_y), np_text,
                font=self.nowplaying_font,
                fill=(200, 180, 240)
            )

            # ── THUMBNAIL — left inside card ──
            thumb_size = 340
            thumb_x = cx1 + 45
            thumb_y = cy1 + (cy2 - cy1 - thumb_size) // 2

            # Glow behind thumb
            glow_t = Image.new("RGBA", bg.size, (0, 0, 0, 0))
            gt = ImageDraw.Draw(glow_t)
            for i in range(20, 0, -1):
                alpha = int(60 * (i / 20))
                gt.rounded_rectangle(
                    [thumb_x - i, thumb_y - i,
                     thumb_x + thumb_size + i, thumb_y + thumb_size + i],
                    radius=24 + i,
                    fill=(100, 40, 200, alpha)
                )
            bg = Image.alpha_composite(bg, glow_t)
            draw = ImageDraw.Draw(bg)

            with Image.open(temp) as raw_art:
                art = square_crop(raw_art.convert("RGBA"))
                art = art.resize((thumb_size, thumb_size))

            self._paste_rounded(bg, art, (thumb_x, thumb_y), radius=22)

            draw = ImageDraw.Draw(bg)
            draw.rounded_rectangle(
                [thumb_x - 2, thumb_y - 2,
                 thumb_x + thumb_size + 2, thumb_y + thumb_size + 2],
                radius=24,
                outline=(255, 255, 255, 35),
                width=2
            )

            # ── RIGHT SIDE INFO ──
            info_x = thumb_x + thumb_size + 55
            info_max_w = cx2 - info_x - 40
            card_h = cy2 - cy1

            # Vertical center calculation
            line_h = self.title_font_sm.size + 8
            total_h = (
                line_h * 2 +
                14 +
                self.meta_font.size +
                10 +
                self.small_font.size +
                32 +
                6 +
                14 +
                self.time_font.size +
                32 +
                self.ctrl_font.size + 16
            )
            start_y = cy1 + (card_h - total_h) // 2

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

            # ── VIEWS ──
            meta_y = title_end_y + 14
            views = song.view_count or "Unknown"
            draw.text(
                (info_x, meta_y),
                f"YouTube  •  {views}",
                font=self.meta_font, fill=(180, 150, 225)
            )

            # ── REQUESTED BY ──
            req_y = meta_y + self.meta_font.size + 10
            requested_by = getattr(song, 'requested_by', None)
            if requested_by:
                name = getattr(
                    requested_by, 'first_name', '') or str(requested_by)
                draw.text(
                    (info_x, req_y), f"▸  Requested by  {name}",
                    font=self.small_font, fill=(140, 100, 210)
                )

            # ── PROGRESS BAR ──
            bar_x1 = info_x
            bar_x2 = cx2 - 45
            bar_y = req_y + self.small_font.size + 32
            bar_h = 6
            bar_w = bar_x2 - bar_x1
            fill_w = int(bar_w * 0.38)

            # Track
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x2, bar_y + bar_h],
                radius=3, fill=(255, 255, 255, 35)
            )
            # Fill — Spotify green
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x1 + fill_w, bar_y + bar_h],
                radius=3, fill=(29, 185, 84)
            )
            # Dot
            dot_x = bar_x1 + fill_w
            dot_y = bar_y + bar_h // 2
            draw.ellipse(
                [dot_x - 9, dot_y - 9, dot_x + 9, dot_y + 9],
                fill=(255, 255, 255)
            )

            # Time
            time_y = bar_y + bar_h + 12
            draw.text(
                (bar_x1, time_y), "00:00",
                font=self.time_font, fill=(160, 130, 205)
            )
            duration = getattr(song, 'duration', '0:00')
            dur_w = self.time_font.getlength(duration)
            draw.text(
                (bar_x2 - dur_w, time_y), duration,
                font=self.time_font, fill=(160, 130, 205)
            )

            # ── CONTROLS ──
            ctrl_y = time_y + self.time_font.size + 28
            ctrl_cx = (info_x + bar_x2) // 2
            spacing = int((bar_x2 - info_x) // 5)

            controls = [
                ("⇄", (170, 140, 220)),
                ("⏮", (210, 185, 245)),
                ("▶", (255, 255, 255)),
                ("⏭", (210, 185, 245)),
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
                        [x - r, ctrl_y - 6,
                         x + r, ctrl_y + self.ctrl_font.size + 6],
                        fill=(255, 255, 255)
                    )
                    sw = int(self.ctrl_font.getlength(symbol))
                    draw.text(
                        (x - sw // 2 + 2, ctrl_y),
                        symbol, font=self.ctrl_font, fill=(18, 8, 38)
                    )
                else:
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
