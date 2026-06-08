"""Pre-fetch models so the first translation run is fast.

Usage:
    python -m src.model_downloader --type hf   --repo facebook/nllb-200-distilled-600M
    python -m src.model_downloader --type gguf --repo TheBloke/some-GGUF --file model.Q4_K_M.gguf
    python -m src.model_downloader --type paddleocr --lang ch
    python -m src.model_downloader --type fonts

Also runnable as a script:  python src/model_downloader.py ...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import (
    FONTS_DIR,
    HF_MODEL_DIR,
    NOTO_SANS_CJK_URL,
    NOTO_SANS_URL,
    OCR_LANG,
    PADDLEOCR_MODEL_DIR,
)
from .utils import LOGGER, ensure_dir, setup_logging


def _download(url: str, dest: Path) -> Path:
    import urllib.request

    LOGGER.info("Downloading %s -> %s", url, dest)
    ensure_dir(dest.parent)
    req = urllib.request.Request(url, headers={"User-Agent": "papiocr/0.1"})
    with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as fh:
        total = int(resp.headers.get("Content-Length", 0))
        read = 0
        chunk = 1 << 16
        while True:
            buf = resp.read(chunk)
            if not buf:
                break
            fh.write(buf)
            read += len(buf)
            if total:
                pct = 100.0 * read / total
                LOGGER.info("  %6.2f%%  %d / %d bytes", pct, read, total)
    return dest


def _hf(repo: str, local_dir: Path) -> Path:
    from huggingface_hub import snapshot_download  # type: ignore

    LOGGER.info("snapshot_download(%s, local_dir=%s)", repo, local_dir)
    path = snapshot_download(
        repo_id=repo,
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,  # type: ignore[call-arg]
    )
    LOGGER.info("HF model ready at %s", path)
    return Path(path)


def _gguf(repo: str, filename: str, local_dir: Path) -> Path:
    from huggingface_hub import hf_hub_download  # type: ignore

    LOGGER.info("hf_hub_download(%s, %s)", repo, filename)
    path = hf_hub_download(
        repo_id=repo,
        filename=filename,
        local_dir=str(local_dir),
    )
    LOGGER.info("GGUF file ready at %s", path)
    return Path(path)


def _paddleocr(lang: str) -> Path:
    """PaddleOCR lazily downloads its own model files on first use; we just
    trigger a one-line detection pass with a tiny dummy image to warm the
    cache into PADDLEOCR_MODEL_DIR if the user has it configured."""
    from paddleocr import PaddleOCR  # type: ignore

    import numpy as np

    LOGGER.info("Warming PaddleOCR (lang=%s)...", lang)
    ocr = PaddleOCR(use_angle_cls=False, lang=lang, show_log=False, det_model_dir=str(PADDLEOCR_MODEL_DIR / "det"), rec_model_dir=str(PADDLEOCR_MODEL_DIR / "rec"), cls_model_dir=str(PADDLEOCR_MODEL_DIR / "cls"))
    blank = (np.ones((32, 128, 3), dtype="uint8") * 255)
    ocr.ocr(blank, cls=False)
    LOGGER.info("PaddleOCR models cached under %s", PADDLEOCR_MODEL_DIR)
    return PADDLEOCR_MODEL_DIR


def _fonts() -> list[Path]:
    out: list[Path] = []
    targets = [
        (NOTO_SANS_URL, FONTS_DIR / "NotoSans-Regular.ttf"),
        (NOTO_SANS_CJK_URL, FONTS_DIR / "NotoSansCJK-Regular.otf"),
    ]
    for url, dest in targets:
        if dest.exists() and dest.stat().st_size > 1024:
            LOGGER.info("Already have %s (%d bytes)", dest, dest.stat().st_size)
            out.append(dest)
            continue
        try:
            _download(url, dest)
            out.append(dest)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to download %s: %s", url, exc)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="model_downloader")
    p.add_argument(
        "--type",
        required=True,
        choices=["hf", "gguf", "paddleocr", "fonts"],
    )
    p.add_argument("--repo", help="HF or GGUF repo id (hf/gguf).")
    p.add_argument("--file", help="GGUF filename (gguf).")
    p.add_argument("--lang", default=OCR_LANG, help="PaddleOCR lang (paddleocr).")
    p.add_argument("--local-dir", default=None, help="Override local dir.")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)
    setup_logging(verbose := __import__("logging").DEBUG if args.verbose else __import__("logging").INFO)

    if args.type == "hf":
        if not args.repo:
            LOGGER.error("--repo required for hf type")
            return 2
        target = Path(args.local_dir) if args.local_dir else HF_MODEL_DIR / args.repo
        _hf(args.repo, target)
    elif args.type == "gguf":
        if not args.repo or not args.file:
            LOGGER.error("--repo and --file required for gguf type")
            return 2
        target = Path(args.local_dir) if args.local_dir else HF_MODEL_DIR / "gguf"
        _gguf(args.repo, args.file, target)
    elif args.type == "paddleocr":
        _paddleocr(args.lang)
    elif args.type == "fonts":
        paths = _fonts()
        for pth in paths:
            LOGGER.info("font ready: %s", pth)
    return 0


if __name__ == "__main__":
    sys.exit(main())
