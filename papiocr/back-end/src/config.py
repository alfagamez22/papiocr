"""Centralized configuration and paths."""
from __future__ import annotations

from pathlib import Path

# ----- Paths -----
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
FONTS_DIR = PROJECT_ROOT / "fonts"
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
HF_MODEL_DIR = MODELS_DIR / "hf"
GGUF_MODEL_DIR = MODELS_DIR / "gguf"
PADDLEOCR_MODEL_DIR = MODELS_DIR / "paddleocr"

# Make sure model dirs exist so PaddleOCR and HF land somewhere predictable.
for _p in (HF_MODEL_DIR, GGUF_MODEL_DIR, PADDLEOCR_MODEL_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# ----- OCR -----
# PaddleOCR language codes. Common ones:
#   "ch"  : Chinese + English (Simplified)
#   "chinese_cht" : Traditional Chinese
#   "en"  : English
#   "japan", "korean", "french", "german", "ru", "ar", ...
OCR_LANG = "ch"
OCR_USE_ANGLE_CLS = True
MIN_CONFIDENCE = 0.0  # keep everything by default; user can filter later

# ----- Translator -----
# NLLB-200 distilled: one model, 200 languages, requires explicit lang codes.
TRANSLATION_MODEL = "facebook/nllb-200-distilled-600M"
DEFAULT_SOURCE_LANG = "zho_Hans"  # NLLB code for Simplified Chinese
DEFAULT_TARGET_LANG = "eng_Latn"  # NLLB code for English

# Mapping from common 2-letter codes to NLLB codes; anything not here is passed
# through unchanged (NLLB accepts its own codes directly).
NLLB_CODE_MAP = {
    "zh": "zho_Hans",
    "zh-cn": "zho_Hans",
    "zh-hans": "zho_Hans",
    "zh-tw": "zho_Hant",
    "zh-hant": "zho_Hant",
    "en": "eng_Latn",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "es": "spa_Latn",
    "pt": "por_Latn",
    "ru": "rus_Cyrl",
    "ar": "arb_Arab",
    "hi": "hin_Deva",
    "it": "ita_Latn",
}

# Helsinki-NLP/opus-mt-* uses 2-letter ISO codes; we detect that family by name
# and route appropriately.
HF_OPUS_FAMILIES = ("Helsinki-NLP/opus-mt",)

# ----- Image processing -----
INPAINT_RADIUS = 3
TEXT_PADDING = 6           # pixels around OCR box when building the mask
RING_SAMPLE_PIXELS = 8     # width of the ring used to sample background color
RENDER_MIN_FONT = 10       # smallest font size the renderer will use
RENDER_MAX_FONT = 200      # safety cap
RENDER_LINE_SPACING = 1.15 # multiplier on font size for multi-line

# ----- Fonts -----
DEFAULT_FONT_NAME = "NotoSans-Regular.ttf"
DEFAULT_CJK_FONT_NAME = "NotoSansCJK-Regular.otf"
# Public-domain / open-license font URLs used to bootstrap the fonts/ folder.
NOTO_SANS_URL = (
    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf"
)
NOTO_SANS_CJK_URL = (
    "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/"
    "NotoSansCJKsc-Regular.otf"
)
