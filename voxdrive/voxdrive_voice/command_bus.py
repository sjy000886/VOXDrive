"""File-based command handoff between VoxDrive ASR/NLU and driving agents."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_DIR = REPO_ROOT / "voxdrive" / "runtime"
DEFAULT_COMMAND_PATH = DEFAULT_RUNTIME_DIR / "voice_command.json"


def write_command(command: Dict[str, Any], path: Path = DEFAULT_COMMAND_PATH) -> Dict[str, Any]:
    """Atomically write the latest accepted voice command."""
    command_path = Path(path)
    command_path.parent.mkdir(parents=True, exist_ok=True)

    payload = dict(command)
    payload["received_wall_time"] = time.time()
    payload["sequence_id"] = time.time_ns()

    tmp_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(command_path.parent),
            prefix=command_path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_name = tmp.name
            json.dump(payload, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
        os.replace(tmp_name, command_path)
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.unlink(tmp_name)

    return payload


def read_command(
    path: Path = DEFAULT_COMMAND_PATH,
    max_age_seconds: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Read the latest voice command, returning None for missing/stale data."""
    command_path = Path(path)
    try:
        with command_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    if not isinstance(payload, dict):
        return None

    if max_age_seconds is not None:
        received_at = payload.get("received_wall_time")
        try:
            age = time.time() - float(received_at)
        except (TypeError, ValueError):
            return None
        if age > max_age_seconds:
            return None

    return payload

