#!/usr/bin/env python
"""Transcribe microphone audio in short chunks with local SenseVoice."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import soundfile as sf


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_DIR = REPO_ROOT / "ckpts" / "SenseVoiceSmall"
DEFAULT_VAD_DIR = REPO_ROOT / "ckpts" / "fsmn-vad"


def strip_sensevoice_tags(text: str) -> str:
    return re.sub(r"<\|[^|]+?\|>", "", text).strip()


def list_arecord_devices() -> None:
    subprocess.run(["arecord", "-l"], check=False)


def choose_device(requested: str) -> str:
    if requested != "auto":
        return requested
    import torch

    return "cuda:0" if torch.cuda.is_available() else "cpu"


def build_model(args: argparse.Namespace) -> object:
    from funasr import AutoModel

    model_kwargs = {
        "model": str(args.model_dir.resolve()),
        "trust_remote_code": True,
        "device": choose_device(args.infer_device),
        "disable_update": True,
        "disable_pbar": True,
    }
    if args.vad_dir and args.vad_dir.exists():
        model_kwargs["vad_model"] = str(args.vad_dir.resolve())
        model_kwargs["vad_kwargs"] = {"max_single_segment_time": 30000}
    return AutoModel(**model_kwargs)


def transcribe_chunk(model: object, wav_path: Path, args: argparse.Namespace) -> list[dict]:
    result = model.generate(
        input=str(wav_path),
        cache={},
        language=args.language,
        use_itn=not args.no_itn,
        batch_size_s=max(args.chunk_seconds, 1),
        merge_vad=args.merge_vad,
        merge_length_s=15,
    )
    for item in result:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            item["clean_text"] = strip_sensevoice_tags(item["text"])
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-devices", action="store_true", help="Print arecord capture devices and exit.")
    parser.add_argument(
        "--alsa-device",
        default=os.environ.get("VOXDRIVE_ALSA_DEVICE", "plughw:CARD=Camera,DEV=0"),
        help="ALSA capture device, e.g. default, plughw:CARD=Camera,DEV=0, plughw:0,0.",
    )
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--chunk-seconds", type=float, default=2.0)
    parser.add_argument("--rms-threshold", type=float, default=0.001, help="Skip chunks quieter than this RMS.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--vad-dir", type=Path, default=DEFAULT_VAD_DIR)
    parser.add_argument("--infer-device", default="cuda:0", help="auto, cpu, cuda:0, ...")
    parser.add_argument("--language", default="zh", help="auto, zh, en, yue, ja, ko.")
    parser.add_argument("--merge-vad", action="store_true")
    parser.add_argument("--no-itn", action="store_true")
    parser.add_argument("--keep-wavs", type=Path, default=None, help="Optional directory to keep chunk wavs.")
    parser.add_argument("--raw-json", action="store_true", help="Print full JSON result instead of clean text only.")
    parser.add_argument("--max-chunks", type=int, default=0, help="Stop after N chunks. Default: 0 means run forever.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_devices:
        list_arecord_devices()
        return 0

    if not args.model_dir.exists():
        raise FileNotFoundError(f"ASR model directory not found: {args.model_dir}")

    if args.keep_wavs:
        args.keep_wavs.mkdir(parents=True, exist_ok=True)

    print("Loading ASR model...")
    model = build_model(args)
    print("Model ready. Press Ctrl+C to stop.")

    bytes_per_sample = 2
    samples_per_chunk = int(args.sample_rate * args.chunk_seconds)
    bytes_per_chunk = samples_per_chunk * args.channels * bytes_per_sample
    command = [
        "arecord",
        "-q",
        "-D",
        args.alsa_device,
        "-f",
        "S16_LE",
        "-r",
        str(args.sample_rate),
        "-c",
        str(args.channels),
        "-t",
        "raw",
    ]

    print("Capture command:", " ".join(command))
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stop_process(*_: object) -> None:
        if proc.poll() is None:
            proc.terminate()

    signal.signal(signal.SIGINT, stop_process)
    signal.signal(signal.SIGTERM, stop_process)

    chunk_id = 0
    try:
        while proc.poll() is None:
            assert proc.stdout is not None
            raw = proc.stdout.read(bytes_per_chunk)
            if len(raw) < bytes_per_chunk:
                break

            audio_i16 = np.frombuffer(raw, dtype="<i2")
            audio_f32 = audio_i16.astype(np.float32) / 32768.0
            rms = float(np.sqrt(np.mean(np.square(audio_f32)))) if audio_f32.size else 0.0

            chunk_id += 1
            if rms < args.rms_threshold:
                print(f"[{chunk_id:04d}] silence rms={rms:.4f}")
                continue

            wav_dir = args.keep_wavs or Path(tempfile.gettempdir())
            wav_path = wav_dir / f"voxdrive_mic_{int(time.time())}_{chunk_id:04d}.wav"
            sf.write(wav_path, audio_i16.reshape(-1, args.channels), args.sample_rate, subtype="PCM_16")

            started = time.perf_counter()
            result = transcribe_chunk(model, wav_path, args)
            elapsed = time.perf_counter() - started

            if not args.keep_wavs:
                wav_path.unlink(missing_ok=True)

            if args.raw_json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                texts = [item.get("clean_text", "") for item in result if isinstance(item, dict)]
                text = " ".join(t for t in texts if t).strip()
                print(f"[{chunk_id:04d}] rms={rms:.4f} asr={elapsed:.2f}s {text}")

            if args.max_chunks and chunk_id >= args.max_chunks:
                break
    finally:
        stop_process()
        stderr = b""
        if proc.stderr is not None:
            stderr = proc.stderr.read()
        if stderr:
            sys.stderr.write(stderr.decode(errors="ignore"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
