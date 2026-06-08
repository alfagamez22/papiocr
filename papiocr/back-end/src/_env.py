"""Cross-platform environment fixes applied before any heavy imports.

Three things happen here, in order:

1. Point Hugging Face at `<project>/models/hf` so model weights live with
   the project instead of in the user's `~/.cache/huggingface`.
2. On Windows: reorder PATH so the venv's torch lib dir is searched first,
   strip CUDA 13+ (its OpenMP runtime is incompatible with torch's
   bundled libiomp5md.dll and causes `WinError 127 ... shm.dll`), and set
   `KMP_DUPLICATE_LIB_OK=TRUE` as a belt-and-braces measure.
3. Pre-import `torch` so its DLLs load exactly once; subsequent
   paddleocr / transformers imports see a cached `torch` module and skip
   the DLL load.

Importing this module is side-effect-only; callers should `import src._env`
*before* importing torch / paddle / paddleocr / transformers.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Hugging Face cache -> <project>/models/hf
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_HF_CACHE = _PROJECT_ROOT / "models" / "hf"
_HF_CACHE.mkdir(parents=True, exist_ok=True)
# HF reads these at import time. Set them BEFORE huggingface_hub is loaded.
os.environ.setdefault("HF_HOME", str(_HF_CACHE))
os.environ.setdefault("HF_HUB_CACHE", str(_HF_CACHE))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(_HF_CACHE))
os.environ.setdefault("TRANSFORMERS_CACHE", str(_HF_CACHE))

if sys.platform == "win32":
    # Quiet a few noisy warnings.
    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
    os.environ.setdefault("PYTHONWARNINGS", "ignore::DeprecationWarning,ignore::UserWarning")

    # 2. Re-order PATH so the venv's torch lib dir is searched first.
    venv_torch_lib = (
        _PROJECT_ROOT
        / ".venv"
        / "Lib"
        / "site-packages"
        / "torch"
        / "lib"
    )
    if venv_torch_lib.exists():
        try:
            os.add_dll_directory(str(venv_torch_lib))  # type: ignore[attr-defined]
        except OSError:
            pass
        # Strip CUDA 13+ from PATH for this process — its OpenMP runtime
        # is incompatible with the bundled libiomp5md.dll and causes
        # `WinError 127 ... shm.dll` at torch import time. Also clear
        # CUDA env vars so torch doesn't try to probe CUDA 13.
        for var in ("CUDA_PATH", "CUDA_HOME", "CUDA_ROOT"):
            os.environ.pop(var, None)
        parts = [
            p
            for p in os.environ.get("PATH", "").split(os.pathsep)
            if "CUDA\\v13" not in p and "CUDA/v13" not in p
        ]
        if str(venv_torch_lib) not in parts:
            parts.insert(0, str(venv_torch_lib))
        os.environ["PATH"] = os.pathsep.join(parts)

    # Make duplicate OpenMP tolerable (belt + braces).
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("KMP_INIT_AT_FORK", "FALSE")

    # 3. Pre-import torch so its DLLs are loaded exactly once. After this,
    # any subsequent `import torch` in paddleocr / transformers just
    # returns the cached module and skips the DLL load.
    try:
        import torch  # type: ignore  # noqa: F401
    except Exception:
        # If torch is not installed yet (e.g. user is mid-install), do not
        # crash here — let the rest of the package import gracefully and
        # surface the real error when the user actually uses an engine.
        pass
