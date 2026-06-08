"""Quick venv activator.

Usage:
    python env.py              Print activation instructions
    python env.py <cmd> [args] Run <cmd> inside the venv

Examples:
    python env.py python -m pytest -q
    python env.py python src/main.py --image input/sample.png --source zh --target en
    python env.py pip install -r requirements-cpu.txt
    python env.py powershell     Open a new PowerShell with the venv active
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

VENV_ROOT = Path(__file__).resolve().parent / ".venv"
ACTIVATE_PS1 = VENV_ROOT / "Scripts" / "Activate.ps1"
PYTHON_EXE = VENV_ROOT / "Scripts" / "python.exe"
PIP_EXE = VENV_ROOT / "Scripts" / "pip.exe"


def _is_active() -> bool:
    return sys.prefix != sys.base_prefix


def _activate_ps1_str() -> str:
    return f'& "{ACTIVATE_PS1}"'


def main() -> int:
    args = sys.argv[1:]

    if _is_active():
        if not args:
            print(f"venv is already active: {sys.prefix}")
            return 0
        # Already active — resolve exe to the venv's Python/pip so PATH
        # doesn't pick up a different installation.
        first = args[0].lower()
        if first == "python":
            exe = sys.executable
            cmd_args = args[1:]
        elif first == "pip":
            exe = str(PIP_EXE)
            cmd_args = args[1:]
        elif args[0].startswith("-"):
            # Treat --version, -c, -m foo etc. as python flags
            exe = sys.executable
            cmd_args = args
        else:
            # Anything else (pytest, black, ruff, etc.) runs via shell PATH
            return subprocess.call(args, shell=True)
        return subprocess.call([exe] + cmd_args, shell=False)

    if not VENV_ROOT.exists():
        print(f"ERROR: venv not found at {VENV_ROOT}")
        print("Run: python -m venv .venv")
        return 1

    if not args:
        print(f"Activate manually:")
        print(f"    {_activate_ps1_str()}")
        print(f"Or run a command inside the venv:")
        print(f"    python env.py python src/main.py --image input/sample.png ...")
        return 0

    first = args[0].lower()
    if first == "python":
        exe = str(PYTHON_EXE)
        cmd_args = args[1:]
    elif first == "pip":
        exe = str(PIP_EXE)
        cmd_args = args[1:]
    elif first == "powershell":
        subprocess.call(
            ["powershell.exe", "-NoExit", "-Command", _activate_ps1_str()],
            shell=False,
        )
        return 0
    elif first == "cmd":
        subprocess.call(
            ["cmd.exe", "/k", f'"{VENV_ROOT / "Scripts" / "activate.bat"}"'],
            shell=False,
        )
        return 0
    else:
        exe = str(PYTHON_EXE)
        cmd_args = args

    full_cmd = " ".join([exe] + cmd_args)
    print(f"[venv] {full_cmd}")
    return subprocess.call([exe] + cmd_args, shell=False)


if __name__ == "__main__":
    sys.exit(main())
