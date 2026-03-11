#!/usr/bin/env python3
"""Verify that requirements.txt is in sync with requirements.in."""
from pathlib import Path
import difflib
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
REQ_IN = ROOT / "requirements.in"
REQ_TXT = ROOT / "requirements.txt"


def main() -> int:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        cmd = [
            str(ROOT / "venv" / "bin" / "pip-compile"),
            "--quiet",
            "--no-header",
            "--strip-extras",
            "--output-file",
            str(tmp_path),
            "requirements.in",
        ]
        subprocess.run(cmd, check=True, cwd=ROOT)

        current = REQ_TXT.read_text().splitlines()
        generated = tmp_path.read_text().splitlines()

        if current == generated:
            print("requirements.txt is up to date")
            return 0

        print("requirements.txt is out of date with requirements.in")
        diff = difflib.unified_diff(
            current,
            generated,
            fromfile="requirements.txt",
            tofile="generated",
            lineterm="",
        )
        for line in diff:
            print(line)
        return 1
    finally:
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
