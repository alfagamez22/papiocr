"""Translation via Hugging Face Transformers (NLLB / opus-mt)."""
from __future__ import annotations

import re
from typing import Sequence

from .config import (
    DEFAULT_SOURCE_LANG,
    DEFAULT_TARGET_LANG,
    HF_OPUS_FAMILIES,
    NLLB_CODE_MAP,
    TRANSLATION_MODEL,
)
from .utils import LOGGER


_NUMERIC_OR_SYMBOL_RE = re.compile(
    r"^[\s\d.,:;+/\\%#@()（）\[\]【】{}<>·\-–—_!?'\"|&=~]+$"
)
_REPEATED_COMPACT_WORD_RE = re.compile(r"([A-Za-z]{2,24})(?:\1){5,}")
_NUMERIC_OR_SYMBOL_RE = re.compile(
    r"^[\s\d.,:;+/\\%#@()\[\]{}<>@._!?'\"|&=~*-]+$"
)
_SOCIAL_METADATA_RE = re.compile(
    r"^@.+(?:\d+\s*(?:hours?|days?|hrs?|mins?)\s*ago|\d+\s*[hdm])?$",
    re.I,
)


def should_preserve_source_text(text: str) -> bool:
    """Return True for OCR fragments that should not be machine translated."""
    value = text.strip()
    if not value:
        return True
    if value.startswith("@") or _SOCIAL_METADATA_RE.search(value):
        return True
    if _NUMERIC_OR_SYMBOL_RE.fullmatch(value):
        return True
    return False


def looks_like_repetitive_translation(text: str) -> bool:
    """Detect model hallucinations such as JoeJoeJoeJoe..."""
    value = text.strip()
    if len(value) < 48:
        return False

    compact = re.sub(r"[^A-Za-z]+", "", value)
    if len(compact) >= 36 and _REPEATED_COMPACT_WORD_RE.search(compact):
        return True

    words = re.findall(r"[A-Za-z]{2,24}", value.lower())
    if len(words) >= 10:
        most_common = max(words.count(word) for word in set(words))
        if most_common / len(words) >= 0.65:
            return True
        unique_short = {word for word in words if len(word) <= 4}
        if len(unique_short) <= 2 and len(words) >= 16:
            return True

    return False


def postprocess_translation(source: str, translated: str) -> str:
    """Keep renderer-safe output when a model produces unusable text."""
    source = source.strip()
    translated = translated.strip()
    if should_preserve_source_text(source):
        return source
    if looks_like_repetitive_translation(translated):
        LOGGER.warning("Dropping repetitive translation for OCR text: %r", source)
        return source
    return translated


# ---------------------------------------------------------------------------
# Hugging Face
# ---------------------------------------------------------------------------
class HFTranslator:
    """Translation using `transformers.pipeline("translation", ...)`.

    Supports two families:
      - NLLB-200 (e.g. facebook/nllb-200-distilled-600M): use NLLB lang codes
        like "zho_Hans" / "eng_Latn", passed via `src_lang` / `tgt_lang`.
      - Helsinki-NLP/opus-mt-*: use 2-letter codes, no special kwargs.

    The appropriate family is auto-detected from the model repo id.
    """

    def __init__(
        self,
        model_name: str = TRANSLATION_MODEL,
        source_lang: str = DEFAULT_SOURCE_LANG,
        target_lang: str = DEFAULT_TARGET_LANG,
        device: str = "cpu",
    ):
        from transformers import pipeline  # type: ignore

        self.model_name = model_name
        self.source_lang = self._normalize_src(source_lang)
        self.target_lang = self._normalize_tgt(target_lang)
        self._is_nllb = "nllb" in model_name.lower()

        kwargs = {"model": model_name}
        if device and device != "cpu":
            kwargs["device"] = device
        LOGGER.info(
            "Loading translation pipeline %s (src=%s, tgt=%s, device=%s)",
            model_name,
            self.source_lang,
            self.target_lang,
            device,
        )
        self.pipeline = pipeline("translation", **kwargs)

    # ------------------------------------------------------------------ utils
    def _normalize_src(self, lang: str) -> str:
        if not self._looks_like_nllb(str(self.model_name).lower()):
            return lang
        return NLLB_CODE_MAP.get(lang.lower(), lang)

    def _normalize_tgt(self, lang: str) -> str:
        if not self._looks_like_nllb(str(self.model_name).lower()):
            return lang
        return NLLB_CODE_MAP.get(lang.lower(), lang)

    @staticmethod
    def _looks_like_nllb(model_name_lower: str) -> bool:
        return "nllb" in model_name_lower

    @property
    def is_nllb(self) -> bool:
        return self._is_nllb

    # ------------------------------------------------------------ translation
    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        if should_preserve_source_text(text):
            return text.strip()
        if self.is_nllb:
            out = self.pipeline(
                text,
                src_lang=self.source_lang,
                tgt_lang=self.target_lang,
                max_length=512,
            )
        else:
            # opus-mt takes the source lang implicitly via the model choice;
            # we still call with no extra kwargs.
            out = self.pipeline(text, max_length=512)
        return postprocess_translation(text, out[0]["translation_text"])

    def translate_batch(self, texts: Sequence[str]) -> list[str]:
        results: list[str | None] = [None] * len(texts)
        pending: list[tuple[int, str]] = []

        for index, text in enumerate(texts):
            if not text or not text.strip():
                results[index] = ""
            elif should_preserve_source_text(text):
                results[index] = text.strip()
            else:
                pending.append((index, text))

        if not pending:
            return [r or "" for r in results]

        cleaned = [text for _, text in pending]
        if self.is_nllb:
            outs = self.pipeline(
                cleaned,
                src_lang=self.source_lang,
                tgt_lang=self.target_lang,
                max_length=512,
            )
        else:
            outs = self.pipeline(cleaned, max_length=512)

        for (index, source), output in zip(pending, outs):
            results[index] = postprocess_translation(source, output["translation_text"])

        return [r or "" for r in results]

