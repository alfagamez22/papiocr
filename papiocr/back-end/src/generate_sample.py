"""Generate input/sample.png with a mix of Chinese text on white + dark banner.

Run from the project root:
    python src/generate_sample.py

Used so the MVP has something to translate before the user supplies their own.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import FONTS_DIR, INPUT_DIR
from .utils import find_first_existing, setup_logging

setup_logging()


def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        FONTS_DIR / "NotoSansCJK-Regular.otf",
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
    f = find_first_existing(candidates)
    if f is None:
        return ImageFont.load_default()  # type: ignore[return-value]
    return ImageFont.truetype(str(f), size=size)  # type: ignore[return-value]


def make_sample(out_path: Path) -> Path:
    W, H = 1200, 800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    # Top heading on white.
    draw.text((60, 60), "深度学习模型市场", font=_font(46), fill="black")
    draw.text(
        (60, 130),
        "PaddleOCR + Hugging Face 文本翻译演示",
        font=_font(28),
        fill=(80, 80, 80),
    )

    # Dark navy banner across the middle.
    banner_y0, banner_y1 = 220, 360
    draw.rectangle([(0, banner_y0), (W, banner_y1)], fill=(15, 33, 82))
    draw.text(
        (60, banner_y0 + 50),
        "极限长周期智能体",
        font=_font(56),
        fill=(255, 255, 255),
    )
    draw.text(
        (60, banner_y0 + 115),
        "新一代开源框架",
        font=_font(32),
        fill=(220, 220, 220),
    )

    # White card with a colored title bar.
    card_x0, card_y0, card_x1, card_y1 = 60, 420, 1140, 720
    draw.rectangle([(card_x0, card_y0), (card_x1, card_y1)], outline=(180, 180, 180), width=2)
    draw.rectangle([(card_x0, card_y0), (card_x1, card_y0 + 60)], fill=(220, 50, 47))
    draw.text(
        (card_x0 + 18, card_y0 + 14),
        "阿里巴巴达摩院",
        font=_font(34),
        fill="white",
    )
    draw.text(
        (card_x0 + 18, card_y0 + 80),
        "大规模预训练语言模型",
        font=_font(30),
        fill="black",
    )
    draw.text(
        (card_x0 + 18, card_y0 + 130),
        "支持中英日韩多语言翻译",
        font=_font(28),
        fill=(60, 60, 60),
    )
    draw.text(
        (card_x0 + 18, card_y0 + 200),
        "完全开源 · 本地运行 · 离线推理",
        font=_font(26),
        fill=(40, 40, 40),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path


def make_synthetic_no_cjk(out_path: Path) -> Path:
    """Fallback that draws Latin-only text, in case no CJK font is installed."""
    W, H = 1200, 800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    draw.text((60, 60), "Deep Learning Model Market", font=_font(46), fill="black")
    draw.text(
        (60, 130),
        "PaddleOCR + Hugging Face text translation demo",
        font=_font(28),
        fill=(80, 80, 80),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path


if __name__ == "__main__":
    out = INPUT_DIR / "sample.png"
    try:
        make_sample(out)
        print(f"Wrote {out}")
    except Exception as exc:  # noqa: BLE001
        print(f"generate_sample failed: {exc}; falling back to synthetic Latin image.")
        out = INPUT_DIR / "sample.png"
        make_synthetic_no_cjk(out)
        print(f"Wrote {out}")
