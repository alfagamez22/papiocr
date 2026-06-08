"""Text removal: mask, inpaint, solid-fill, auto-detection.

Two strategies are exposed:

- `inpaint_text(image, mask, radius)`     -> cv2.inpaint (TELEA).  Default.
- `fill_solid(image, mask)`               -> paint the mask with the average
                                              color sampled from a thin ring
                                              around each box.  Best for
                                              flat-color backgrounds (web
                                              cards, banners).
- `remove_text(image, boxes, padding, mode)` -> convenience that builds the
                                              mask and applies the chosen
                                              strategy in one call.
"""
from __future__ import annotations

from typing import Iterable, Literal, Sequence

import cv2
import numpy as np

from .config import INPAINT_RADIUS, RING_SAMPLE_PIXELS, TEXT_PADDING
from .utils import LOGGER, box_to_rect, expand_box

RemovalMode = Literal["inpaint", "solid", "auto"]


# ---------------------------------------------------------------------------
# Mask
# ---------------------------------------------------------------------------
def create_mask(
    image_shape: tuple[int, int, int],
    boxes: Sequence[Sequence[Sequence[float]]],
    padding: int = TEXT_PADDING,
) -> np.ndarray:
    """Create a uint8 mask (0 or 255) covering all expanded boxes."""
    h, w = image_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    if not boxes:
        return mask
    for box in boxes:
        expanded = expand_box(box, padding)
        pts = np.array(expanded, dtype=np.int32)
        cv2.fillPoly(mask, [pts], 255)
    return mask


# ---------------------------------------------------------------------------
# Inpainting
# ---------------------------------------------------------------------------
def inpaint_text(
    image: np.ndarray,
    mask: np.ndarray,
    radius: int = INPAINT_RADIUS,
) -> np.ndarray:
    if mask.sum() == 0:
        return image
    return cv2.inpaint(image, mask, radius, cv2.INPAINT_TELEA)


# ---------------------------------------------------------------------------
# Solid fill (mean color of a thin ring around the box)
# ---------------------------------------------------------------------------
def _sample_ring_color(
    image: np.ndarray, box: Sequence[Sequence[float]], thickness: int
) -> np.ndarray:
    """Mean BGR color of a `thickness`-wide ring just outside the box."""
    rect_mask = np.zeros(image.shape[:2], dtype=np.uint8)
    expanded = expand_box(box, thickness)
    cv2.fillPoly(rect_mask, [np.array(expanded, dtype=np.int32)], 255)
    # Subtract the inner solid to leave only the ring.
    inner = np.zeros(image.shape[:2], dtype=np.uint8)
    cv2.fillPoly(inner, [np.array(box, dtype=np.int32)], 255)
    ring_mask = cv2.subtract(rect_mask, inner)
    pixels = image[ring_mask > 0]
    if pixels.size == 0:
        # Fall back to the whole expanded region's mean.
        pixels = image[rect_mask > 0]
    if pixels.size == 0:
        return np.array([255, 255, 255], dtype=np.uint8)
    mean = pixels.mean(axis=0)
    return np.clip(mean, 0, 255).astype(np.uint8)


def fill_solid(
    image: np.ndarray,
    mask: np.ndarray,
    boxes: Sequence[Sequence[Sequence[float]]] | None = None,
    ring_thickness: int = RING_SAMPLE_PIXELS,
) -> np.ndarray:
    """Paint each masked region with the mean color of its surrounding ring."""
    out = image.copy()
    if mask.sum() == 0 or not boxes:
        # No boxes -> fall back to global mean of unmasked pixels.
        if mask.sum() == 0:
            return out
        mean = image[mask == 0].mean(axis=0) if (mask == 0).any() else np.array([255, 255, 255])
        out[mask > 0] = np.clip(mean, 0, 255).astype(np.uint8)
        return out

    for box in boxes:
        color = _sample_ring_color(image, box, ring_thickness)
        region_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.fillPoly(
            region_mask,
            [np.array(expand_box(box, 2), dtype=np.int32)],
            255,
        )
        out[region_mask > 0] = color
    return out


# ---------------------------------------------------------------------------
# Auto
# ---------------------------------------------------------------------------
def _background_is_flat(image: np.ndarray, box: Sequence[Sequence[float]]) -> bool:
    """Heuristic: is the area around the box near-uniform in color?"""
    rect = box_to_rect(box)
    x, y, w, h = rect
    H, W = image.shape[:2]
    pad = max(6, int(0.25 * max(w, h)))
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(W, x + w + pad)
    y1 = min(H, y + h + pad)
    crop = image[y0:y1, x0:x1]
    if crop.size == 0:
        return False
    std = float(crop.std(axis=(0, 1)).mean())
    return std < 12.0  # very low variance => flat


def remove_text(
    image: np.ndarray,
    boxes: Sequence[Sequence[Sequence[float]]],
    padding: int = TEXT_PADDING,
    mode: RemovalMode = "auto",
    inpaint_radius: int = INPAINT_RADIUS,
) -> tuple[np.ndarray, np.ndarray]:
    """Build mask from `boxes` and apply the chosen removal strategy.

    Returns (cleaned_image, mask).
    """
    mask = create_mask(image.shape, list(boxes), padding=padding)
    if mask.sum() == 0:
        LOGGER.info("No text regions to remove.")
        return image.copy(), mask

    if mode == "inpaint":
        cleaned = inpaint_text(image, mask, inpaint_radius)
    elif mode == "solid":
        cleaned = fill_solid(image, mask, boxes)
    elif mode == "auto":
        flat = all(_background_is_flat(image, b) for b in boxes)
        if flat:
            LOGGER.info("Auto removal: solid fill (flat backgrounds).")
            cleaned = fill_solid(image, mask, boxes)
        else:
            LOGGER.info("Auto removal: inpainting (varied backgrounds).")
            cleaned = inpaint_text(image, mask, inpaint_radius)
    else:
        raise ValueError(f"Unknown removal mode: {mode!r}")

    return cleaned, mask
