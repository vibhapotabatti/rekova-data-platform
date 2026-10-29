"""The seed must produce byte-identical feeds on every run (CI reproducibility)."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _digests(directory: Path) -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.glob("*.csv"))
    }


def test_generator_is_deterministic(raw_dir, tmp_path):
    env = {**os.environ, "REKOVA_RAW_DIR": str(tmp_path)}
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_data.py")],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
    )
    assert _digests(raw_dir) == _digests(tmp_path)
    assert len(_digests(tmp_path)) == 7
