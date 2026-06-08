"""Shared helpers: I/O, box math, logging."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

LOGGER = logging.getLogger("papiocr")


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger once."""
    if LOGGER.handlers:
        return
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    LOGGER.addHandler(handler)
    LOGGER.setLevel(level)
    LOGGER.propagate = False


def ensure_dir(path: Path | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_image_bgr(path: Path | str) -> np.ndarray:
    """Read an image as BGR (OpenCV convention)."""
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    return img


def save_image_bgr(image: np.ndarray, path: Path | str) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    ok = cv2.imwrite(str(p), image)
    if not ok:
        raise IOError(f"cv2.imwrite failed for {p}")


def box_to_rect(box: Sequence[Sequence[float]]) -> tuple[int, int, int, int]:
    """Convert a 4-point polygon to an integer (x, y, w, h) rectangle."""
    xs = [float(p[0]) for p in box]
    ys = [float(p[1]) for p in box]
    x0, x1 = int(round(min(xs))), int(round(max(xs)))
    y0, y1 = int(round(min(ys))), int(round(max(ys)))
    return x0, y0, max(1, x1 - x0), max(1, y1 - y0)


def box_center(box: Sequence[Sequence[float]]) -> tuple[float, float]:
    xs = [float(p[0]) for p in box]
    ys = [float(p[1]) for p in box]
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0


def expand_box(
    box: Sequence[Sequence[float]], padding: int
) -> list[list[int]]:
    """Expand a 4-point polygon outward by `padding` pixels on every side."""
    xs = [float(p[0]) for p in box]
    ys = [float(p[1]) for p in box]
    x0, x1 = min(xs) - padding, max(xs) + padding
    y0, y1 = min(ys) - padding, max(ys) + padding
    return [
        [int(round(x0)), int(round(y0))],
        [int(round(x1)), int(round(y0))],
        [int(round(x1)), int(round(y1))],
        [int(round(x0)), int(round(y1))],
    ]


def find_first_existing(paths: Sequence[Path | str]) -> Path | None:
    for p in paths:
        p = Path(p)
        if p.exists() and p.is_file():
            return p
    return None


def color_distance_bgr(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """Cheap perceptual-ish distance between two BGR colors (Euclidean)."""
    return float(sum((int(x) - int(y)) ** 2 for x, y in zip(a, b)) ** 0.5)
