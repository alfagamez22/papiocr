"""PaddleOCR wrapper.

Returns a normalized list of detections:
    [{"text": str, "box": [[x,y], ...4], "confidence": float}, ...]
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .config import MIN_CONFIDENCE, OCR_USE_ANGLE_CLS, PADDLEOCR_MODEL_DIR
from .utils import LOGGER, ensure_dir


@dataclass
class Detection:
    text: str
    box: list[list[float]]
    confidence: float

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "box": [[float(p[0]), float(p[1])] for p in self.box],
            "confidence": float(self.confidence),
        }


class OCREngine:
    """Thin wrapper around PaddleOCR.

    Importing paddleocr is deferred to __init__ so that the rest of the
    package can be imported on systems without paddlepaddle installed.

    Model weights are pinned to `models/paddleocr/{det,rec,cls}/<lang>/` so
    they live inside the project, not in the user's `~/.paddleocr/`.
    """

    def __init__(self, lang: str = "ch", use_angle_cls: bool = OCR_USE_ANGLE_CLS):
        from paddleocr import PaddleOCR  # type: ignore

        # PaddleOCR uses the convention <root>/whl/{det,rec,cls}/<lang>/<model>.
        # We mirror that under <project>/models/paddleocr/ so the weights live
        # with the project, not in the user's `~/.paddleocr/whl/`.
        det_dir = ensure_dir(PADDLEOCR_MODEL_DIR / "whl" / "det" / lang)
        rec_dir = ensure_dir(PADDLEOCR_MODEL_DIR / "whl" / "rec" / lang)
        cls_dir = ensure_dir(PADDLEOCR_MODEL_DIR / "whl" / "cls")

        LOGGER.info(
            "Initializing PaddleOCR (lang=%s, angle_cls=%s, det_dir=%s)",
            lang,
            use_angle_cls,
            det_dir,
        )
        self.ocr = PaddleOCR(
            use_angle_cls=use_angle_cls,
            lang=lang,
            show_log=False,
            det_model_dir=str(det_dir),
            rec_model_dir=str(rec_dir),
            cls_model_dir=str(cls_dir),
        )

    def detect(self, image_path: str | Path) -> list[Detection]:
        """Run OCR on a file path and return normalized detections."""
        result = self.ocr.ocr(str(image_path), cls=True)
        detections: list[Detection] = []
        if not result:
            return detections

        # PaddleOCR returns: [ [ [box, (text, conf)], ... ] ] for one image
        # but newer versions may omit the outer list. Handle both.
        pages = result if isinstance(result[0], list) else [result]
        for page in pages:
            if page is None:
                continue
            for line in page:
                if not line or len(line) < 2:
                    continue
                box = line[0]
                text, conf = line[1]
                if conf is None or conf < MIN_CONFIDENCE:
                    continue
                detections.append(
                    Detection(
                        text=str(text),
                        box=[[float(p[0]), float(p[1])] for p in box],
                        confidence=float(conf),
                    )
                )
        LOGGER.info("OCR detected %d text region(s)", len(detections))
        return detections

    def detect_from_array(self, image_bgr) -> list[Detection]:
        """Run OCR on a BGR numpy array (writes to a temp file under the hood
        because PaddleOCR's python API is happiest with file paths)."""
        import tempfile

        import cv2

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
            tmp_path = Path(fh.name)
        try:
            cv2.imwrite(str(tmp_path), image_bgr)
            return self.detect(tmp_path)
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass


def filter_by_confidence(
    detections: Sequence[Detection], min_conf: float
) -> list[Detection]:
    return [d for d in detections if d.confidence >= min_conf]
