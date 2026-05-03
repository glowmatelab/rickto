# ==============================================================================
# _thumbnails.py - Apple Music Style Thumbnail
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
                "Elevenyts/helpers/Raleway-Bold.ttf", 52)
            self.title_font_sm = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 40)
            self.artist_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 30)
            self.time_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 26)
            self.small_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 20)
            self.badge_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf", 18)
            self.ctrl_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 52)
            self.ctrl_sm_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf", 38)
        except OSError:
            self.title_font = self.title_font_sm = self.artist_font = \
                self.time_font = self.small_font = self.badge_font = \
                self.ctrl_font = self.ctrl_sm_font = ImageFont.load_default()

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

    def _generate_sync(self, temp, output, song, size=(1280, 720)):
        try:
            W, H = size

            # ── BACKGROUND — blurred thumbnail ──
            with Image.open(temp) as raw:
                bg = raw.resize((W, H)).convert("RGBA")

            bg = bg.filter(ImageFilter.GaussianBlur(40))

            # Dark overlay
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 155))
            bg = Image.alpha_composite(bg, overlay)

            # Vignette
            vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            vd = ImageDraw.Draw(vig)
            for i in range(150):
                alpha = int(220 * (i / 150))
                vd.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, alpha))
            bg = Image.alpha_composite(bg, vig)

            draw = ImageDraw.Draw(bg)

            # ── LEFT — THUMBNAIL ──
            thumb_pad = 55
            thumb_size = H - thumb_pad * 2
            thumb_x = thumb_pad
            thumb_y = thumb_pad

            with Image.open(temp) as raw_art:
                art = square_crop(raw_art.convert("RGBA"))
                art = art.resize((thumb_size, thumb_size))

            self._paste_rounded(bg, art, (thumb_x, thumb_y), radius=24)

            draw = ImageDraw.Draw(bg)

            # ── RIGHT SIDE ──
            right_x = thumb_x + thumb_size + 60
            right_max_w = W - right_x - 60
            right_center = right_x + right_max_w // 2

            # ── TITLE ──
            title_raw = re.sub(r"\W+", " ", song.title).title()
            title_trimmed = trim_to_width(
                title_raw, self.title_font, right_max_w)

            title_y = thumb_y + 30
            # Shadow
            for dx, dy in [(-2, 2), (2, 2)]:
                draw.text(
                    (right_x + dx, title_y + dy),
                    title_trimmed,
                    font=self.title_font,
                    fill=(0, 0, 0, 100)
                )
            draw.text(
                (right_x, title_y),
                title_trimmed,
                font=self.title_font,
                fill=(255, 255, 255)
            )

            # ── ARTIST / CHANNEL ──
            artist_y = title_y + self.title_font.size + 12
            views = song.view_count or "Unknown"
            draw.text(
                (right_x, artist_y),
                f"YouTube  •  {views}",
                font=self.artist_font,
                fill=(200, 200, 200)
            )

            # ── PROGRESS BAR ──
            bar_y = artist_y + self.artist_font.size + 55
            bar_x1 = right_x
            bar_x2 = W - 60
            bar_h = 5
            bar_w = bar_x2 - bar_x1
            fill_w = int(bar_w * 0.38)

            # Track bg
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x2, bar_y + bar_h],
                radius=3, fill=(255, 255, 255, 80)
            )
            # Fill — white
            draw.rounded_rectangle(
                [bar_x1, bar_y, bar_x1 + fill_w, bar_y + bar_h],
                radius=3, fill=(255, 255, 255)
            )

            # ── GALAXY BOTS BADGE — center of bar ──
            badge_text = "Galaxy Bots"
            badge_tw = self.badge_font.getlength(badge_text)
            badge_pad_x = 14
            badge_pad_y = 5
            badge_w = badge_tw + badge_pad_x * 2
            badge_h = self.badge_font.size + badge_pad_y * 2
            badge_x = bar_x1 + (bar_w - badge_w) // 2
            badge_y = bar_y - badge_h // 2 - 2

            # Badge bg
            badge_bg = Image.new("RGBA", (int(badge_w), int(badge_h)), (0, 0, 0, 0))
            ImageDraw.Draw(badge_bg).rounded_rectangle(
                (0, 0, badge_w, badge_h),
                radius=8,
                fill=(50, 50, 50, 200)
            )
            bg.paste(badge_bg, (int(badge_x), int(badge_y)), badge_bg)
            draw = ImageDraw.Draw(bg)
            draw.text(
                (badge_x + badge_pad_x, badge_y + badge_pad_y),
                badge_text,
                font=self.badge_font,
                fill=(220, 220, 220)
            )

            # ── TIME LABELS ──
            time_y = bar_y + bar_h + 14
            draw.text(
                (bar_x1, time_y), "0:00",
                font=self.time_font, fill=(200, 200, 200)
            )
            duration = getattr(song, 'duration', '0:00')
            dur_label = f"-{duration}"
            dur_w = self.time_font.getlength(dur_label)
            draw.text(
                (bar_x2 - dur_w, time_y), dur_label,
                font=self.time_font, fill=(200, 200, 200)
            )

            # ── CONTROLS ── ⏮ ⏸ ⏭
            ctrl_y = time_y + self.time_font.size + 38
            ctrl_cx = right_x + right_max_w // 2
            spacing = 160

            # Prev
            prev_sym = "⏮"
            prev_w = int(self.ctrl_sm_font.getlength(prev_sym))
            draw.text(
                (ctrl_cx - spacing - prev_w // 2, ctrl_y),
                prev_sym,
                font=self.ctrl_sm_font,
                fill=(255, 255, 255)
            )

            # Pause — bigger center
            pause_sym = "⏸"
            pause_w = int(self.ctrl_font.getlength(pause_sym))
            draw.text(
                (ctrl_cx - pause_w // 2, ctrl_y - 8),
                pause_sym,
                font=self.ctrl_font,
                fill=(255, 255, 255)
            )

            # Next
            next_sym = "⏭"
            next_w = int(self.ctrl_sm_font.getlength(next_sym))
            draw.text(
                (ctrl_cx + spacing - next_w // 2, ctrl_y),
                next_sym,
                font=self.ctrl_sm_font,
                fill=(255, 255, 255)
            )

            # ── VOLUME BAR ──
            vol_y = ctrl_y + self.ctrl_font.size + 40
            vol_icon_x = right_x
            vol_x1 = right_x + 30
            vol_x2 = bar_x2 - 30
            vol_h = 4

            # Vol icon left
            draw.text(
                (vol_icon_x, vol_y - 2), "◁",
                font=self.small_font, fill=(180, 180, 180)
            )
            # Vol icon right
            vol_r_icon = "◁))"
            vol_r_w = self.small_font.getlength(vol_r_icon)
            draw.text(
                (bar_x2 - vol_r_w, vol_y - 2), vol_r_icon,
                font=self.small_font, fill=(180, 180, 180)
            )

            # Vol track
            draw.rounded_rectangle(
                [vol_x1, vol_y + 4, vol_x2, vol_y + 4 + vol_h],
                radius=2, fill=(255, 255, 255, 60)
            )
            # Vol fill — 65%
            vol_fill = int((vol_x2 - vol_x1) * 0.65)
            draw.rounded_rectangle(
                [vol_x1, vol_y + 4, vol_x1 + vol_fill, vol_y + 4 + vol_h],
                radius=2, fill=(255, 255, 255, 180)
            )
            # Vol dot
            vdot_x = vol_x1 + vol_fill
            vdot_y = vol_y + 4 + vol_h // 2
            draw.ellipse(
                [vdot_x - 8, vdot_y - 8, vdot_x + 8, vdot_y + 8],
                fill=(255, 255, 255)
            )

            # ── BOTTOM ICONS — chat + queue ──
            bottom_y = vol_y + 50
            bottom_cx = ctrl_cx

            draw.text(
                (bottom_cx - 80, bottom_y), "💬",
                font=self.small_font, fill=(200, 200, 200)
            )
            draw.text(
                (bottom_cx + 50, bottom_y), "☰",
                font=self.small_font, fill=(200, 200, 200)
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
