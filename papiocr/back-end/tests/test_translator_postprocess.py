from __future__ import annotations

from src.translator import (
    looks_like_repetitive_translation,
    postprocess_translation,
    should_preserve_source_text,
)


def test_preserves_social_metadata_rows():
    source = "@周小小闹（大学宿舍）·1天前"

    assert should_preserve_source_text(source)
    assert postprocess_translation(source, "@JoeJoeJoeJoeJoeJoeJoe") == source


def test_preserves_numeric_and_symbol_fragments():
    assert should_preserve_source_text("2166.9")
    assert should_preserve_source_text("#")
    assert postprocess_translation("2166.9", "The following is a list of countries") == "2166.9"


def test_repetitive_translation_falls_back_to_source():
    source = "大学女生遇到富豪人设骗局"
    repeated = "Joe" * 40

    assert looks_like_repetitive_translation(repeated)
    assert postprocess_translation(source, repeated) == source


def test_comma_separated_repetition_falls_back_to_source():
    source = "no lo."
    repeated = "No, no, no, no, no, no, no, no, no, no, no, no, no, no, no, no."

    assert looks_like_repetitive_translation(repeated)
    assert postprocess_translation(source, repeated) == source


def test_normal_translation_is_kept():
    assert not should_preserve_source_text("寻找格桑先生")
    assert postprocess_translation("寻找格桑先生", "Looking for Mr. Gesang") == "Looking for Mr. Gesang"
