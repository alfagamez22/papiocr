"""End-to-end image translation pipeline."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from .config import (
    OUTPUT_DIR,
    RENDER_MAX_TEXT_TO_BOX_RATIO,
    RENDER_MIN_BOX_AREA,
    RENDER_MIN_BOX_HEIGHT,
    RENDER_MIN_BOX_WIDTH,
    RENDER_MIN_FONT,
)
from .ocr import Detection, OCREngine
from .remover import RemovalMode, remove_text
from .renderer import RenderItem, draw_translated
from .translator import HFTranslator, looks_like_repetitive_translation, should_preserve_source_text
from .utils import LOGGER, box_to_rect, ensure_dir, load_image_bgr


@dataclass
class TranslatedItem:
    original_text: str
    translated_text: str
    box: list[list[float]]
    confidence: float

    def as_dict(self) -> dict:
        return {
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "box": self.box,
            "confidence": self.confidence,
        }


class ImageTranslationPipeline:
    def __init__(
        self,
        ocr_lang: str = "ch",
        translation_model: str = "facebook/nllb-200-distilled-600M",
        source_lang: str = "zho_Hans",
        target_lang: str = "eng_Latn",
        removal_mode: RemovalMode = "auto",
    ):
        self.ocr = OCREngine(lang=ocr_lang)
        self.translator = HFTranslator(
            model_name=translation_model,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        self.removal_mode = removal_mode

    # ------------------------------------------------------------- helpers
    def _translate_detections(
        self, detections: Sequence[Detection]
    ) -> list[TranslatedItem]:
        if not detections:
            return []
        texts = [d.text for d in detections]
        LOGGER.info("Translating %d line(s)...", len(texts))
        translated = self.translator.translate_batch(texts)
        out: list[TranslatedItem] = []
        for det, t in zip(detections, translated):
            out.append(
                TranslatedItem(
                    original_text=det.text,
                    translated_text=t,
                    box=det.box,
                    confidence=det.confidence,
                )
            )
        return out

    @staticmethod
    def _dump_corrections(
        items: Sequence[TranslatedItem], path: Path
    ) -> None:
        ensure_dir(path.parent)
        with path.open("w", encoding="utf-8") as fh:
            json.dump([i.as_dict() for i in items], fh, ensure_ascii=False, indent=2)

    @staticmethod
    def _is_renderable_item(item: TranslatedItem, image_shape: tuple[int, ...]) -> bool:
        text = item.translated_text.strip()
        if not text:
            return False
        if looks_like_repetitive_translation(text):
            return False
        if should_preserve_source_text(item.original_text):
            return False

        x, y, w, h = box_to_rect(item.box)
        image_h, image_w = image_shape[:2]
        if x >= image_w or y >= image_h:
            return False
        if w < RENDER_MIN_BOX_WIDTH or h < RENDER_MIN_BOX_HEIGHT:
            return False
        if w * h < RENDER_MIN_BOX_AREA:
            return False

        capacity = max(12, int((w * h * RENDER_MAX_TEXT_TO_BOX_RATIO) / (RENDER_MIN_FONT * 5.2)))
        if len(text) > capacity:
            LOGGER.warning(
                "Skipping overlong translation (%d chars, capacity %d): %r",
                len(text),
                capacity,
                item.original_text,
            )
            return False
        return True

    # ------------------------------------------------------------- public
    def run(
        self,
        image_path: str | Path,
        output_path: str | Path | None = None,
        corrections: str | Path | None = None,
        no_render: bool = False,
    ) -> dict:
        """Run the full pipeline and return a result dict.

        keys: image_path, output_path, corrections_path, items, num_items
        """
        image_path = Path(image_path)
        if output_path is None:
            output_path = OUTPUT_DIR / f"{image_path.stem}_translated.png"
        output_path = Path(output_path)
        ensure_dir(output_path.parent)
        corrections_path = output_path.with_suffix(".corrections.json")

        image = load_image_bgr(image_path)
        detections = self.ocr.detect(image_path)
        if not detections:
            LOGGER.warning("No text detected in %s", image_path)
            # Still save a copy of the input so users see something happened.
            if not no_render:
                cv2.imwrite(str(output_path), image)
            result_items: list[TranslatedItem] = []
            self._dump_corrections(result_items, corrections_path)
            return {
                "image_path": str(image_path),
                "output_path": str(output_path),
                "corrections_path": str(corrections_path),
                "items": [],
                "num_items": 0,
            }

        translated_items = self._translate_detections(detections)

        # Apply manual corrections if provided.
        if corrections is not None:
            self._apply_corrections(translated_items, Path(corrections))

        renderable_items = [
            t for t in translated_items if self._is_renderable_item(t, image.shape)
        ]
        skipped = len(translated_items) - len(renderable_items)
        if skipped:
            LOGGER.info("Skipped %d OCR region(s) that were too small or noisy to render.", skipped)

        boxes = [list(t.box) for t in renderable_items]
        cleaned, _mask = remove_text(image, boxes, mode=self.removal_mode)  # type: ignore[arg-type]

        render_items = [
            RenderItem(
                text=t.translated_text,
                box=t.box,
                original_text=t.original_text,
                confidence=t.confidence,
            )
            for t in renderable_items
        ]

        if no_render:
            LOGGER.info("Skipping render (--no-render); only writing corrections.")
        else:
            draw_translated(cleaned, render_items, output_path)
            LOGGER.info("Wrote %s", output_path)

        self._dump_corrections(translated_items, corrections_path)
        LOGGER.info("Wrote %s", corrections_path)

        return {
            "image_path": str(image_path),
            "output_path": str(output_path),
            "corrections_path": str(corrections_path),
            "items": [t.as_dict() for t in translated_items],
            "num_items": len(translated_items),
            "num_rendered": len(renderable_items),
        }

    # ------------------------------------------------------------- static
    @staticmethod
    def _apply_corrections(items: list[TranslatedItem], path: Path) -> None:
        """Replace translated_text with values from a corrections JSON file.

        Match strategy: same `original_text`. If a manual entry has a
        different original_text it is matched by box overlap (>= 50% IoU).
        """
        with path.open("r", encoding="utf-8") as fh:
            overrides = json.load(fh)
        if not isinstance(overrides, list):
            raise ValueError("Corrections file must be a JSON list of objects.")
        by_text = {str(o.get("original_text", "")).strip(): o for o in overrides}

        def _iou(a, b) -> float:
            ax0, ay0 = min(p[0] for p in a), min(p[1] for p in a)
            ax1, ay1 = max(p[0] for p in a), max(p[1] for p in a)
            bx0, by0 = min(p[0] for p in b), min(p[1] for p in b)
            bx1, by1 = max(p[0] for p in b), max(p[1] for p in b)
            ix0, iy0 = max(ax0, bx0), max(ay0, by0)
            ix1, iy1 = min(ax1, bx1), min(ay1, by1)
            iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
            inter = iw * ih
            union = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
            return inter / union if union > 0 else 0.0

        for item in items:
            if item.original_text in by_text:
                new = by_text[item.original_text].get("translated_text", "").strip()
                if new:
                    item.translated_text = new
                continue
            # Fallback: match by best IoU.
            best = max(
                (
                    (_iou(item.box, o.get("box", [])), o)
                    for o in overrides
                    if isinstance(o.get("box"), list) and o.get("box")
                ),
                default=(0.0, None),
                key=lambda x: x[0],
            )
            if best[1] is not None and best[0] >= 0.5:
                new = str(best[1].get("translated_text", "")).strip()
                if new:
                    item.translated_text = new
