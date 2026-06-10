"""Render translated text into the cleaned image with Pillow.

Key responsibilities:
- Choose a font that fits the OCR box (binary-search font size).
- Wrap long English text into multiple lines so it never overflows the box.
- Pick a sensible text color from the cleaned background.
- Optionally draw a thin stroke so light text remains readable on busy bg.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import (
    DEFAULT_CJK_FONT_NAME,
    DEFAULT_FONT_NAME,
    FONTS_DIR,
    RENDER_LINE_SPACING,
    RENDER_MAX_FONT,
    RENDER_MIN_FONT,
)
from .utils import LOGGER, box_to_rect, find_first_existing

# CJK ranges used to decide if a glyph needs the CJK font.
def _is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (
        0x3000 <= o <= 0x303F
        or 0x3400 <= o <= 0x4DBF
        or 0x4E00 <= o <= 0x9FFF
        or 0xF900 <= o <= 0xFAFF
        or 0xFF00 <= o <= 0xFFEF
        or 0x3040 <= o <= 0x309F  # hiragana
        or 0x30A0 <= o <= 0x30FF  # katakana
        or 0xAC00 <= o <= 0xD7AF  # hangul
    )


def _contains_cjk(text: str) -> bool:
    return any(_is_cjk(c) for c in text)


@dataclass
class RenderItem:
    text: str
    box: list[list[float]]
    original_text: str = ""
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Font discovery
# ---------------------------------------------------------------------------
def _candidate_fonts() -> dict[str, list[Path]]:
    return {
        "latin": [
            FONTS_DIR / DEFAULT_FONT_NAME,
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("C:/Windows/Fonts/calibri.ttf"),
        ],
        "cjk": [
            FONTS_DIR / DEFAULT_CJK_FONT_NAME,
            Path("C:/Windows/Fonts/msyh.ttc"),
            Path("C:/Windows/Fonts/simhei.ttf"),
            Path("C:/Windows/Fonts/msyh.ttc"),
        ],
    }


def _load_font(path: Path, size: int) -> ImageFont.ImageFont:
    return ImageFont.truetype(str(path), size=size)  # type: ignore[return-value]


def get_font_for_text(text: str, size: int) -> ImageFont.ImageFont:
    cands = _candidate_fonts()
    prefer = "cjk" if _contains_cjk(text) else "latin"
    order = cands[prefer] + cands["latin" if prefer == "cjk" else "cjk"]
    found = find_first_existing(order)
    if found is None:
        # Pillow ships a default bitmap font as a last resort.
        LOGGER.warning("No TTF font found; falling back to PIL default bitmap font.")
        return ImageFont.load_default()  # type: ignore[return-value]
    return _load_font(found, size)


# ---------------------------------------------------------------------------
# Text fitting
# ---------------------------------------------------------------------------
def _measure(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    """Return (width, height) of `text` rendered with `font`."""
    if hasattr(draw, "textbbox"):
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return int(r - l), int(b - t)
    w, h = draw.textsize(text, font=font)  # type: ignore[attr-defined]
    return int(w), int(h)


def _wrap_text_to_width(
    text: str, font, max_width: int, draw: ImageDraw.ImageDraw
) -> list[str]:
    """Wrap text so each line fits within `max_width` pixels."""
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = current + " " + word
        w, _ = _measure(draw, candidate, font)
        if w <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def fit_font_size(
    text: str,
    font_path: Path,
    max_width: int,
    max_height: int,
    draw: ImageDraw.ImageDraw | None = None,
) -> int:
    """Find the largest font size (>= RENDER_MIN_FONT) whose longest single
    line fits within (max_width, max_height) when measured with `draw`."""
    if draw is None:
        # Caller is fine if we create a throwaway draw to measure.
        from PIL import Image as _Im

        draw = ImageDraw.Draw(_Im.new("RGB", (1, 1)))

    # Upper bound: don't let the font exceed the box height.
    hi = min(RENDER_MAX_FONT, max(8, int(max_height)))
    lo = RENDER_MIN_FONT
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        font = _load_font(font_path, mid)
        lines = _wrap_text_to_width(text, font, max_width, draw)
        line_h = int(mid * RENDER_LINE_SPACING)
        total_h = line_h * len(lines)
        widest = max((_measure(draw, ln, font)[0] for ln in lines), default=0)
        if widest <= max_width and total_h <= max_height:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return max(RENDER_MIN_FONT, best)


# ---------------------------------------------------------------------------
# Color picking
# ---------------------------------------------------------------------------
def _sample_box_color(image_bgr: np.ndarray, box) -> tuple[int, int, int]:
    """Mean BGR color inside the box."""
    x, y, w, h = box_to_rect(box)
    H, W = image_bgr.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return (255, 255, 255)
    crop = image_bgr[y0:y1, x0:x1]
    mean = crop.mean(axis=(0, 1))
    return (int(mean[0]), int(mean[1]), int(mean[2]))


def _contrast_color(bgr: tuple[int, int, int]) -> tuple[int, int, int]:
    """Pick black or white text depending on the box's mean luminance."""
    b, g, r = bgr
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return (0, 0, 0) if luminance > 140 else (255, 255, 255)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def draw_translated(
    image_bgr: np.ndarray,
    items: Sequence[RenderItem],
    output_path: str | Path,
) -> Path:
    """Render `items` into `image_bgr` and save as PNG. Returns the path."""
    img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)

    for item in items:
        if not item.text:
            continue
        x, y, w, h = box_to_rect(item.box)
        # Small inner padding so text doesn't touch the box edge.
        inner_pad = 2
        max_w = max(1, w - 2 * inner_pad)
        max_h = max(1, h - 2 * inner_pad)

        # Pick a font path for measurement.
        cands = _candidate_fonts()
        prefer = "cjk" if _contains_cjk(item.text) else "latin"
        order = cands[prefer] + cands["latin" if prefer == "cjk" else "cjk"]
        font_path = find_first_existing(order)
        if font_path is None:
            LOGGER.warning("No font found; skipping render for %r", item.text)
            continue
        font_size = fit_font_size(item.text, font_path, max_w, max_h, draw)
        font = _load_font(font_path, font_size)
        lines = _wrap_text_to_width(item.text, font, max_w, draw)
        line_h = int(font_size * RENDER_LINE_SPACING)
        total_h = line_h * len(lines)
        widest = max((_measure(draw, ln, font)[0] for ln in lines), default=0)
        if total_h > max_h or widest > max_w:
            LOGGER.warning(
                "Skipping render for text that does not fit OCR box: %r",
                item.text[:80],
            )
            continue

        bg = _sample_box_color(image_bgr, item.box)
        fg = _contrast_color(bg)
        stroke = (255 - fg[0], 255 - fg[1], 255 - fg[2]) if fg == (0, 0, 0) else (0, 0, 0)
        stroke_w = max(1, font_size // 18)

        # Center the text block within the box.
        start_x = x + (w - widest) // 2
        start_y = y + (h - total_h) // 2
        for i, line in enumerate(lines):
            tx = start_x + (widest - _measure(draw, line, font)[0]) // 2
            ty = start_y + i * line_h
            draw.text(
                (tx, ty),
                line,
                font=font,
                fill=fg,
                stroke_width=stroke_w,
                stroke_fill=stroke,
            )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    final = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out), final)
    return out
