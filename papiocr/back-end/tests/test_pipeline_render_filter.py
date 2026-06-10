from __future__ import annotations

from src.pipeline import ImageTranslationPipeline, TranslatedItem


def _item(text: str, box: list[list[float]], original: str = "原文") -> TranslatedItem:
    return TranslatedItem(
        original_text=original,
        translated_text=text,
        box=box,
        confidence=0.99,
    )


def test_render_filter_skips_metadata_rows():
    item = _item(
        "@周小小闹(大学宿舍)",
        [[543, 1008], [763, 1008], [763, 1031], [543, 1031]],
        original="@周小小闹(大学宿舍)",
    )

    assert not ImageTranslationPipeline._is_renderable_item(item, (1600, 2200, 3))


def test_render_filter_skips_repetitive_model_output():
    item = _item(
        "No, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no.",
        [[30, 40], [220, 40], [220, 90], [30, 90]],
        original="no lo.",
    )

    assert not ImageTranslationPipeline._is_renderable_item(item, (1600, 2200, 3))


def test_render_filter_skips_overlong_text_for_box():
    item = _item(
        "Joe" * 80,
        [[543, 1008], [763, 1008], [763, 1031], [543, 1031]],
    )

    assert not ImageTranslationPipeline._is_renderable_item(item, (1600, 2200, 3))


def test_render_filter_keeps_normal_subtitle_box():
    item = _item(
        "Teachers are careful to distinguish!",
        [[240, 825], [680, 825], [680, 860], [240, 860]],
    )

    assert ImageTranslationPipeline._is_renderable_item(item, (1600, 2200, 3))
