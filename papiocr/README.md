# papiocr (PyImageTranslate OCR)

Open-source Python tool that **translates text inside images** and **visually
replaces** the original text with the translation, preserving layout.

Pipeline:

```
Image -> PaddleOCR detect+recognize -> HF Transformers translate
       -> OpenCV inpaint / solid fill -> Pillow re-render -> Output PNG
```

## Features

- 100% Python, no JavaScript, no paid APIs.
- PaddleOCR for text detection and recognition.
- Hugging Face Transformers (NLLB-200 distilled 600M) for translation.
- OpenCV for inpainting; Pillow for text rendering.
- Optional Gradio UI for drag-and-drop preview.
- Optional GGUF local LLM translation backend (v3, not enabled by default).
- Auto-strategy: uses solid fill on flat backgrounds, inpainting otherwise.
- Manual corrections JSON for editing bad translations before re-rendering.

## Quick start

```bash
# 1. Create venv.
#    Python 3.12 is preferred; 3.11 also works. PaddlePaddle does not yet
#    ship wheels for Python 3.14, and torch wheels break on systems that
#    have CUDA 13+ on PATH. Use a dedicated venv.
python -m venv .venv
.venv\Scripts\activate             # Windows
# source .venv/bin/activate        # macOS / Linux

# 2. Install (CPU-friendly pin set; first run downloads ~1.5 GB of model
#    weights into the venv cache and the user's HF cache).
pip install --upgrade pip
pip install -r requirements-cpu.txt

# 3. Generate a synthetic test image (Chinese on white + dark banner).
python src/generate_sample.py

# 4. Translate it.
python src/main.py --image input/sample.png --source zh --target en ^
                   --output output/translated_sample.png
```

The first run downloads:

- PaddleOCR detection / recognition / angle-classification models
  (~50 MB) into `models/paddleocr/whl/{det,rec,cls}/`.
- `facebook/nllb-200-distilled-600M` (~2.5 GB on disk; 600M-parameter
  FP32 weights are larger than the parameter count suggests) into
  `models/hf/hub/`.

Both are redirected to the project by the `src/_env.py` shim (sets
`HF_HOME` / `HF_HUB_CACHE` for Hugging Face, and
`det_model_dir` / `rec_model_dir` / `cls_model_dir` for PaddleOCR), so
nothing lands in your system `~/.cache` or `~/.paddleocr`.

## CLI options

```text
python src/main.py
  --image PATH                Input image (required)
  --source LANG               Source language code (e.g. zh, ja, ko)
  --target LANG               Target language code (e.g. en, es, fr)
  --ocr-lang CODE             PaddleOCR model code (ch, en, japan, korean, ...)
  --translation-model REPO    HF repo id; default facebook/nllb-200-distilled-600M
  --output PATH               Output PNG path. Default: output/<stem>_translated.png
  --removal-mode {inpaint,solid,auto}
                              Text removal strategy (default: auto).
  --corrections PATH          Optional manual corrections JSON (see below).
  --no-render                 Skip re-rendering; only produce corrections JSON.
  --debug-boxes PATH          Draw OCR boxes on a copy and save to this path.
  --verbose                   Verbose logging.
```

You can run the CLI either way:

```bash
python src/main.py --image input/sample.png --source zh --target en
python -m src.main --image input/sample.png --source zh --target en
```

## Gradio UI

```bash
pip install gradio
python src/app.py
```

Opens a browser at `http://127.0.0.1:7860` with a drag-and-drop interface.

## Folder layout

```
papiocr/
  .venv/                 Python virtualenv (created in step 1 above)
  fonts/                 Bundled open-source fonts
  input/                 Drop images here
  models/                Downloaded model weights (HF, GGUF, PaddleOCR)
    hf/                  Hugging Face cache (HF_HOME is set here)
      hub/
        models--facebook--nllb-200-distilled-600M/  (~2.5 GB)
    paddleocr/
      whl/
        det/ch/ch_PP-OCRv4_det_infer/   (~3 MB)
        rec/ch/ch_PP-OCRv4_rec_infer/   (~10 MB)
        cls/ch_ppocr_mobile_v2.0_cls_infer/  (~1 MB)
    gguf/                (reserved for v3, empty)
  output/                Translated images + corrections JSON
  src/
    main.py              CLI entry
    config.py            Defaults + paths
    _env.py              HF cache redirect + Windows KMP/CUDA shim
    ocr_engine.py        PaddleOCR wrapper (weights pinned to models/paddleocr)
    translator.py        HF (and future GGUF) translator
    text_remover.py      Mask + inpaint / solid fill
    text_renderer.py     Pillow rendering
    model_downloader.py  Pre-fetch HF / GGUF / PaddleOCR assets
    pipeline.py          End-to-end orchestrator
    utils.py             Helpers
    generate_sample.py   Creates input/sample.png for smoke tests
    app.py               Gradio UI
  tests/                 pytest smoke tests
  requirements.txt
  requirements-cpu.txt
  requirements-dev.txt   pytest (install with: pip install -r requirements-dev.txt)
  LICENSE                MIT
```

## Manual corrections

Every run writes `output/<image>.corrections.json`:

```json
[
  {
    "original_text": "极限长周期智能体",
    "translated_text": "Extreme long-cycle agent",
    "box": [[250,390],[560,390],[560,440],[250,440]],
    "confidence": 0.98
  }
]
```

Edit the `translated_text` fields, re-run with `--corrections path.json`, and
the renderer will use your edits instead of fresh translations.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

Five smoke tests verify the synthetic image exists, OCR detects text, mask +
inpaint works, rendering produces a PNG, and the full pipeline emits both
the output image and a valid corrections JSON.

## Known Windows issues & fixes

These are baked into `src/_env.py` so you don't have to deal with them:

1. **CUDA 13+ on PATH** breaks torch 2.x with
   `OSError: [WinError 127] ... shm.dll` because the CUDA 13 OpenMP runtime
   is incompatible with torch's bundled `libiomp5md.dll`. The shim strips
   CUDA 13 from `PATH` and prepends the venv's torch lib dir.
2. **albumentations 1.4+** imports torch via `albumentations.pytorch`
   during PaddleOCR's import chain, which triggers the same DLL load
   failure. We pin `albumentations<1.4`.
3. **transformers 5.x** dropped the `translation` pipeline task. We pin
   `transformers==4.46.0`, the last release that ships it. NLLB works
   fine on 4.46.

If you see any of those errors, the shim isn't being applied — make sure
you activate the venv before running the script.

## License

MIT. See `LICENSE`.
