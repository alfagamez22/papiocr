"""Command-line entry point.

Run as either:
    python src/main.py ...
    python -m src.main ...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import (
    DEFAULT_SOURCE_LANG,
    DEFAULT_TARGET_LANG,
    INPUT_DIR,
    OCR_LANG,
    OUTPUT_DIR,
    TRANSLATION_MODEL,
)
from .ocr import OCREngine
from .pipeline import ImageTranslationPipeline
from .remover import RemovalMode
from .utils import LOGGER, ensure_dir, load_image_bgr, setup_logging


def _make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="papiocr",
        description="Translate text inside images using PaddleOCR + HF Transformers.",
    )
    p.add_argument("--image", required=True, help="Path to input image.")
    p.add_argument("--source", default="zh", help="Source language code (e.g. zh, ja, ko).")
    p.add_argument("--target", default="en", help="Target language code (e.g. en, es, fr).")
    p.add_argument("--ocr-lang", default=OCR_LANG, help="PaddleOCR model code.")
    p.add_argument(
        "--translation-model",
        default=TRANSLATION_MODEL,
        help="Hugging Face model repo id.",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Output PNG path. Default: output/<stem>_translated.png",
    )
    p.add_argument(
        "--removal-mode",
        choices=["inpaint", "solid", "auto"],
        default="auto",
        help="Text removal strategy.",
    )
    p.add_argument(
        "--corrections",
        default=None,
        help="Optional path to a manual corrections JSON file.",
    )
    p.add_argument(
        "--no-render",
        action="store_true",
        help="Skip re-rendering; only produce corrections JSON.",
    )
    p.add_argument(
        "--debug-boxes",
        default=None,
        help="If set, draw OCR boxes on a copy of the input and save to this path.",
    )
    p.add_argument("--verbose", action="store_true", help="Verbose logging.")
    return p


def _draw_debug_boxes(image_path: Path, out_path: Path) -> None:
    import cv2

    from .ocr import OCREngine as _OCR
    from .utils import box_to_rect

    engine = _OCR()
    detections = engine.detect(image_path)
    img = load_image_bgr(image_path)
    for det in detections:
        x, y, w, h = box_to_rect(det.box)
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(
            img,
            f"{det.text[:20]} ({det.confidence:.2f})",
            (x, max(0, y - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )
    ensure_dir(out_path.parent)
    cv2.imwrite(str(out_path), img)
    LOGGER.info("Wrote debug boxes image to %s", out_path)


def main(argv: list[str] | None = None) -> int:
    import logging

    args = _make_parser().parse_args(argv)
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    image_path = Path(args.image)
    if not image_path.exists():
        # Try resolving relative to the bundled input/ dir.
        candidate = INPUT_DIR / args.image
        if candidate.exists():
            image_path = candidate
        else:
            LOGGER.error("Image not found: %s", image_path)
            return 2

    if args.debug_boxes:
        _draw_debug_boxes(image_path, Path(args.debug_boxes))

    output_path = Path(args.output) if args.output else None

    pipeline = ImageTranslationPipeline(
        ocr_lang=args.ocr_lang,
        translation_model=args.translation_model,
        source_lang=args.source,
        target_lang=args.target,
        removal_mode=args.removal_mode,  # type: ignore[arg-type]
    )
    result = pipeline.run(
        image_path=image_path,
        output_path=output_path,
        corrections=args.corrections,
        no_render=args.no_render,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
