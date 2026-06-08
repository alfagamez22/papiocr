"""Translation via Hugging Face Transformers (NLLB / opus-mt)."""
from __future__ import annotations

from typing import Sequence

from .config import (
    DEFAULT_SOURCE_LANG,
    DEFAULT_TARGET_LANG,
    HF_OPUS_FAMILIES,
    NLLB_CODE_MAP,
    TRANSLATION_MODEL,
)
from .utils import LOGGER


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
        return out[0]["translation_text"].strip()

    def translate_batch(self, texts: Sequence[str]) -> list[str]:
        cleaned = [t if t and t.strip() else " " for t in texts]
        if self.is_nllb:
            outs = self.pipeline(
                list(cleaned),
                src_lang=self.source_lang,
                tgt_lang=self.target_lang,
                max_length=512,
            )
        else:
            outs = self.pipeline(list(cleaned), max_length=512)
        return [o["translation_text"].strip() for o in outs]



