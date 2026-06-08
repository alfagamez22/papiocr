"""Smoke tests for papiocr.

These are intentionally lightweight and only verify the wiring works end-to-end
on the synthetic sample image. They DO NOT require GPU; they DO download model
weights on the first run, so allow time on first invocation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.ocr import OCREngine
from src.pipeline import ImageTranslationPipeline
from src.remover import create_mask, inpaint_text
from src.renderer import RenderItem, draw_translated
from src.utils import load_image_bgr

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE = PROJECT_ROOT / "input" / "sample.png"
OUT_DIR = PROJECT_ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)


def test_synthetic_image_exists():
    assert SAMPLE.exists(), f"missing {SAMPLE}; run `python src/generate_sample.py`"


def test_ocr_engine_returns_results():
    engine = OCREngine(lang="ch")
    dets = engine.detect(SAMPLE)
    assert isinstance(dets, list)
    assert len(dets) >= 1, "expected at least one detection on the synthetic image"
    for d in dets:
        assert d.text
        assert len(d.box) == 4
        assert 0.0 <= d.confidence <= 1.0


def test_mask_and_inpaint():
    img = load_image_bgr(SAMPLE)
    engine = OCREngine(lang="ch")
    dets = engine.detect(SAMPLE)
    if not dets:
        pytest.skip("no detections; nothing to test")
    boxes = [d.box for d in dets]
    mask = create_mask(img.shape, boxes, padding=4)
    assert mask.shape == img.shape[:2]
    assert mask.sum() > 0
    cleaned = inpaint_text(img, mask, radius=3)
    assert cleaned.shape == img.shape
    out = OUT_DIR / "test_cleaned.png"
    import cv2

    cv2.imwrite(str(out), cleaned)
    assert out.exists()


def test_renderer_produces_output():
    img = load_image_bgr(SAMPLE)
    engine = OCREngine(lang="ch")
    dets = engine.detect(SAMPLE)
    if not dets:
        pytest.skip("no detections; nothing to test")
    items = [
        RenderItem(
            text=d.text,
            box=d.box,
            original_text=d.text,
            confidence=d.confidence,
        )
        for d in dets
    ]
    out = OUT_DIR / "test_rendered.png"
    draw_translated(img, items, out)
    assert out.exists()


def test_pipeline_end_to_end():
    pipe = ImageTranslationPipeline(
        ocr_lang="ch",
        translation_model="facebook/nllb-200-distilled-600M",
        source_lang="zho_Hans",
        target_lang="eng_Latn",
    )
    out_png = OUT_DIR / "test_pipeline_out.png"
    out_json = OUT_DIR / "test_pipeline_out.corrections.json"
    if out_png.exists():
        out_png.unlink()
    if out_json.exists():
        out_json.unlink()

    result = pipe.run(SAMPLE, output_path=out_png)
    assert result["num_items"] >= 1
    assert out_png.exists()
    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 1
    for entry in data:
        assert "translated_text" in entry
        assert "box" in entry
