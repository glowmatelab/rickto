# ==============================================================================
# _thumbnails.py - Spotify Style Music Player Thumbnail
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
                "Elevenyts/helpers/Raleway-Bold.ttf", 54)
            self.nowplaying_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 20)
            self.meta_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 24)
            self.time_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 22)
            self.small_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 20)
        except OSError:
            self.title_font = self.nowplaying_font = self.meta_font = \
                self.time_font = self.small_font = ImageFont.load_default()

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

    def _draw_glass_card(self, canvas, x1, y1, x2, y2, radius=32):
        # Shadow
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        for i in range(30, 0, -1):
            alpha = int(120 * (i / 30))
            sd.rounded_rectangle(
                [x1 + i, y1 + i // 2, x2 + i, y2 + i // 2],
                radius=radius, fill=(0, 0, 0, alpha)
            )
        merged = Image.alpha_composite(canvas, shadow)
        canvas.paste(merged, (0, 0))

        # Glass fill
        glass = Image.new("RGBA", (x2 - x1, y2 - y1), (20, 10, 40, 200))
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
            outline=(255, 255, 255, 30),
            width=1
        )
        # Inner purple border
        draw.rounded_rectangle(
            [x1 + 2, y1 + 2, x2 - 2, y2 - 2],
            radius=radius - 2,
            outline=(150, 80, 255, 25),
            width=1
        )
        # Top shine
        hl_w = x2 - x1 - radius * 2
        if hl_w > 0:
            shine = Image.new("RGBA", (hl_w, 2), (255, 255, 255, 40))
            canvas.paste(shine, (x1 + radius, y1 + 3), shine)

    def _generate_sync(self, temp, output, song, size=(1280, 720)):
        try:
            W, H = size

            # ── BACKGROUND — blurred thumbnail ──
            with Image.open(temp) as raw:
                bg = raw.resize((W, H)).convert("RGBA")

            bg = bg.filter(ImageFilter.GaussianBlur(35))

            # Dark overlay
            overlay = Image.new("RGBA", (W, H), (5, 2, 15, 185))
            bg = Image.alpha_composite(bg, overlay)

            # Vignette
            vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vd = ImageDraw.Draw(vig)
            for i in range(120):
                alpha = int(200 * (i / 120))
                vd.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, alpha))
            bg = Image.alpha_composite(bg, vig)

            # ── GLASS CARD — center ──
            card_w = 520
            card_h = 640
            cx1 = (W - card_w) // 2
            cy1 = (H - card_h) // 2
            cx2 = cx1 + card_w
            cy2 = cy1 + card_h

            self._draw_glass_card(bg, cx1, cy1, cx2, cy2, radius=36)

            draw = ImageDraw.Draw(bg)

            # ── NOW PLAYING — top center ──
            np_text = "NOW PLAYING"
            np_w = self.nowplaying_font.getlength(np_text)
            np_x = cx1 + (card_w - np_w) // 2
            np_y = cy1 + 28

            # Dot
            draw.ellipse(
                [np_x - 18, np_y + 4, np_x - 6, np_y + 16],
                fill=(29, 185, 84)
            )
            draw.text(
                (np_x, np_y), np_text,
                font=self.nowplaying_font,
                fill=(255, 255, 255, 150)
            )

            # ── ALBUM ART — center top ──
            art_size = 260
            art_x = cx1 + (card_w - art_size) // 2
            art_y = cy1 + 65

            # Glow behind art
            glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            for i in range(25, 0, -1):
                alpha = int(70 * (i / 25))
                gd.rounded_rectangle(
                    [art_x - i, art_y - i,
                     art_x + art_size + i, art_y + art_size + i],
                    radius=20 + i,
                    fill=(100, 40, 200, alpha)
                )
            bg = Image.alpha_composite(bg, glow)
            draw = ImageDraw.Draw(bg)

            with Image.open(temp) as raw_art:
                art = square_crop(raw_art.convert("RGBA"))
                art = art.resize((art_size, art_size))

            self._paste_rounded(bg, art, (art_x, art_y), radius=20)

            # Border around art
            draw = ImageDraw.Draw(bg)
            draw.rounded_rectangle(
                [art_x - 2, art_y - 2,
                 art_x + art_size + 2, art_y + art_size + 2],
                radius=22,
                outline=(255, 255, 255, 40),
                width=2
            )

            # ── SONG TITLE — center ──
            title_y = art_y + art_size + 28
            title = re.sub(r"\W+", " ", song.title).title()

            # Trim to card width
            max_title_w = card_w - 60
            title_trimmed = trim_to_width(title, self.title_font, max_title_w)
            title_w = self.title_font.getlength(title_trimmed)
            title_x = cx1 + (card_w - title_w) // 2

            # Shadow
            for dx, dy in [(-2, 2), (2, 2)]:
                draw.text(
                    (title_x + dx, title_y + dy),
                    title_trimmed,
                    font=self.title_font,
                    fill=(60, 20, 100)
                )
            draw.text(
                (title_x, title_y),
                title_trimmed,
                font=self.title_font,
                fill=(255, 255, 255)
            )

            # ── META — views ──
            meta_y = title_y + self.title_font.size + 10
            views = song.view_count or "Unknown"
            meta_text = f"YouTube  •  {views}"
            meta_w = self.meta_font.getlength(meta_text)
            meta_x = cx1 + (card_w - meta_w) // 2
            draw.text(
                (meta_x, meta_y), meta_text,
                font=self.meta_font,
                fill=(180, 150, 220)
            )

            # ── REQUESTED BY ──
            req_y = meta_y + self.meta_font.size + 8
            requested_by = getattr(song, 'requested_by', None)
            if requested_by:
                name = getattr(requested_by, 'first_name', '') or str(requested_by)
                req_text = f"Requested by  {name}"
                req_w = self.small_font.getlength(req_text)
                req_x = cx1 + (card_w - req_w) // 2
                draw.text(
                    (req_x, req_y), req_text,
                    font=self.small_font,
                    fill=(150, 100, 220)
                )

            # ── PROGRESS BAR ──
            bar_pad = 40
            bar_x1 = cx1 + bar_pad
            bar_x2 = cx2 - bar_pad
            bar_y = req_y + self.small_font.size + 24
            bar_h = 5
            bar_w = bar_x2 - bar_x1
            fill_w = int(bar_w * 0.38)

            # Track
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x2, bar_y + bar_h],
                radius=3, fill=(255, 255, 255, 40)
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
                [dot_x - 8, dot_y - 8, dot_x + 8, dot_y + 8],
                fill=(255, 255, 255)
            )

            # Time labels
            time_y = bar_y + bar_h + 10
            draw.text(
                (bar_x1, time_y), "00:00",
                font=self.time_font, fill=(180, 160, 210)
            )
            duration = getattr(song, 'duration', '0:00')
            dur_w = self.time_font.getlength(duration)
            draw.text(
                (bar_x2 - dur_w, time_y), duration,
                font=self.time_font, fill=(180, 160, 210)
            )

            # ── CONTROLS — center ──
            ctrl_y = time_y + self.time_font.size + 28
            ctrl_cx = cx1 + card_w // 2
            spacing = 90

            controls = [
                ("⇄", 20, (180, 150, 220)),   # shuffle
                ("⏮", 36, (220, 200, 255)),   # prev
                ("▶", 44, (255, 255, 255)),   # play — white circle
                ("⏭", 36, (220, 200, 255)),   # next
                ("↺", 20, (180, 150, 220)),   # repeat
            ]
            positions = [
                ctrl_cx - spacing * 2,
                ctrl_cx - spacing,
                ctrl_cx,
                ctrl_cx + spacing,
                ctrl_cx + spacing * 2,
            ]

            for (symbol, size_px, color), x in zip(controls, positions):
                try:
                    font = ImageFont.truetype(
                        "Elevenyts/helpers/Raleway-Bold.ttf", size_px)
                except:
                    font = self.small_font

                if symbol == "▶":
                    # White circle bg
                    r = 32
                    draw.ellipse(
                        [x - r, ctrl_y - 8,
                         x + r, ctrl_y + size_px + 8],
                        fill=(255, 255, 255)
                    )
                    # Dark play symbol
                    sw = font.getlength(symbol)
                    draw.text(
                        (x - int(sw // 2) + 2, ctrl_y),
                        symbol, font=font, fill=(20, 10, 40)
                    )
                else:
                    sw = font.getlength(symbol)
                    draw.text(
                        (x - int(sw // 2), ctrl_y),
                        symbol, font=font, fill=color
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
