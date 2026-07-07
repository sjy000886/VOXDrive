#!/usr/bin/env python
"""Run a local FunASR/SenseVoice transcription test."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import torch
from funasr import AutoModel


def choose_device(requested: str) -> str:
    if requested != "auto":
        return requested
    return "cuda:0" if torch.cuda.is_available() else "cpu"


def existing_dir(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path) if path.exists() else None


def add_clean_text(result: object) -> object:
    if not isinstance(result, list):
        return result

    for item in result:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            item["clean_text"] = re.sub(r"<\|[^|]+?\|>", "", item["text"]).strip()
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True, type=Path, help="Audio file path.")
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path("ckpts/SenseVoiceSmall"),
        help="Local ASR model directory.",
    )
    parser.add_argument(
        "--vad-dir",
        type=Path,
        default=Path("ckpts/fsmn-vad"),
        help="Optional local VAD model directory.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="Inference device, e.g. auto, cpu, cuda:0.",
    )
    parser.add_argument(
        "--language",
        default="auto",
        help="SenseVoice language setting: auto, zh, en, yue, ja, ko.",
    )
    parser.add_argument("--batch-size-s", type=int, default=60)
    parser.add_argument("--no-itn", action="store_true", help="Disable inverse text normalization.")
    parser.add_argument("--merge-vad", action="store_true", help="Merge VAD segments for long audio.")
    parser.add_argument("--raw-only", action="store_true", help="Do not add cleaned text without SenseVoice tags.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_dir = args.model_dir.resolve()
    audio_path = args.audio.resolve()

    if not model_dir.exists():
        raise FileNotFoundError(f"ASR model directory not found: {model_dir}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    device = choose_device(args.device)
    vad_dir = existing_dir(args.vad_dir.resolve())

    model_kwargs = {
        "model": str(model_dir),
        "trust_remote_code": True,
        "device": device,
        "disable_update": True,
    }
    if vad_dir:
        model_kwargs["vad_model"] = vad_dir
        model_kwargs["vad_kwargs"] = {"max_single_segment_time": 30000}

    model = AutoModel(**model_kwargs)
    result = model.generate(
        input=str(audio_path),
        cache={},
        language=args.language,
        use_itn=not args.no_itn,
        batch_size_s=args.batch_size_s,
        merge_vad=args.merge_vad,
        merge_length_s=15,
    )

    if not args.raw_only:
        result = add_clean_text(result)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
