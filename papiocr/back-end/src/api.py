"""FastAPI REST API for papiocr.

Run:  uvicorn src.api:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import (
    DEFAULT_SOURCE_LANG,
    DEFAULT_TARGET_LANG,
    NLLB_CODE_MAP,
    OUTPUT_DIR,
)
from .documents import auto_translate_document, SUPPORTED_DOC_FORMATS
from .pipeline import ImageTranslationPipeline
from .utils import LOGGER, ensure_dir, setup_logging

setup_logging()
ensure_dir(OUTPUT_DIR)

app = FastAPI(title="papiocr", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "app://."],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        await ws.close()
    except Exception:
        pass

_PIPELINE: ImageTranslationPipeline | None = None


def _get_pipeline(
    source: str = DEFAULT_SOURCE_LANG,
    target: str = DEFAULT_TARGET_LANG,
    ocr_lang: str = "ch",
    model: str = "facebook/nllb-200-distilled-600M",
) -> ImageTranslationPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = ImageTranslationPipeline(
            ocr_lang=ocr_lang,
            translation_model=model,
            source_lang=source,
            target_lang=target,
        )
    return _PIPELINE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SUPPORTED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


def _normalize_lang(code: str) -> str:
    return NLLB_CODE_MAP.get(code.lower(), code)


def _ok(data: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(content=data, status_code=status)


def _err(msg: str, status: int = 400) -> JSONResponse:
    return JSONResponse(content={"error": msg}, status_code=status)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health():
    return _ok({"status": "ok", "version": "0.2.0"})


# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------


@app.get("/api/languages")
def languages():
    codes = sorted(
        {v for v in NLLB_CODE_MAP.values()} | {"eng_Latn", "zho_Hans"}
    )
    return _ok({"languages": codes, "shortcuts": NLLB_CODE_MAP})


# ---------------------------------------------------------------------------
# Text translation
# ---------------------------------------------------------------------------


@app.post("/api/translate/text")
def translate_text(
    text: str = Form(...),
    source: str = Form(DEFAULT_SOURCE_LANG),
    target: str = Form(DEFAULT_TARGET_LANG),
):
    if not text.strip():
        return _err("text is required")
    src = _normalize_lang(source)
    tgt = _normalize_lang(target)
    pipe = _get_pipeline(source=src, target=tgt)
    translated = pipe.translator.translate(text)
    return _ok({"source": src, "target": tgt, "original": text, "translated": translated})


# ---------------------------------------------------------------------------
# Image translation
# ---------------------------------------------------------------------------


@app.post("/api/translate/image")
async def translate_image(
    file: UploadFile = File(...),
    source: str = Form(DEFAULT_SOURCE_LANG),
    target: str = Form(DEFAULT_TARGET_LANG),
):
    ext = Path(file.filename or "image.png").suffix.lower()
    if ext not in _SUPPORTED_IMAGE_EXT:
        return _err(f"Unsupported image format: {ext}")

    src = _normalize_lang(source)
    tgt = _normalize_lang(target)
    pipe = _get_pipeline(source=src, target=tgt)

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    out_name = f"{Path(file.filename or 'image').stem}_{tgt}.png"
    out_path = OUTPUT_DIR / out_name
    ensure_dir(out_path.parent)

    try:
        result = pipe.run(tmp_path, output_path=out_path)
        return FileResponse(
            str(out_path),
            media_type="image/png",
            filename=out_name,
            headers={"X-Items": json.dumps(result["num_items"])},
        )
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Document translation
# ---------------------------------------------------------------------------


@app.post("/api/translate/document")
async def translate_document(
    file: UploadFile = File(...),
    source: str = Form(DEFAULT_SOURCE_LANG),
    target: str = Form(DEFAULT_TARGET_LANG),
):
    ext = Path(file.filename or "file").suffix.lower()
    if ext not in SUPPORTED_DOC_FORMATS:
        return _err(f"Unsupported document format: {ext} (supported: {', '.join(sorted(SUPPORTED_DOC_FORMATS))})")

    src = _normalize_lang(source)
    tgt = _normalize_lang(target)

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        size_mb = tmp_path.stat().st_size / (1024 * 1024)
        if size_mb > 15:
            return _err(f"File too large: {size_mb:.1f} MB (max 15 MB)")

        pipe = _get_pipeline(source=src, target=tgt)
        out_path = auto_translate_document(tmp_path, pipe, ext, src, tgt)
        out_name = f"{Path(file.filename or 'file').stem}_{tgt}{ext}"
        return FileResponse(str(out_path), media_type="application/octet-stream", filename=out_name)
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Manual corrections re-render
# ---------------------------------------------------------------------------


@app.post("/api/translate/render")
async def render_corrections(
    image: UploadFile = File(...),
    corrections: str = Form(...),
    output: str = Form("output.png"),
):
    corrections_data = json.loads(corrections)
    if not isinstance(corrections_data, list):
        return _err("corrections must be a JSON array")

    ext = Path(image.filename or "image.png").suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        shutil.copyfileobj(image.file, tmp)
        img_path = Path(tmp.name)

    corrections_path = OUTPUT_DIR / "manual_corrections.json"
    corrections_path.write_text(corrections, encoding="utf-8")

    out_path = OUTPUT_DIR / output
    pipe = _get_pipeline()
    result = pipe.run(img_path, output_path=out_path, corrections=str(corrections_path))

    return FileResponse(str(out_path), media_type="image/png", filename=output)
