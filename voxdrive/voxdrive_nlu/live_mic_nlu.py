#!/usr/bin/env python
"""Run microphone ASR and map recognized text to VoxDrive NLU commands."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import soundfile as sf


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from voxdrive.voxdrive_asr.live_mic_asr import (  # noqa: E402
    DEFAULT_MODEL_DIR,
    DEFAULT_VAD_DIR,
    build_model,
    list_arecord_devices,
    transcribe_chunk,
)
from voxdrive.voxdrive_nlu.intent_parser import (  # noqa: E402
    DEFAULT_BGE_DIR,
    VoxDriveNLU,
)
from voxdrive.voxdrive_voice.command_bus import (  # noqa: E402
    DEFAULT_COMMAND_PATH,
    write_command,
)


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
    parser.add_argument("--chunk-seconds", type=float, default=2.0, help="Wake-word ASR chunk length.")
    parser.add_argument("--rms-threshold", type=float, default=0.001, help="Skip wake chunks quieter than this RMS.")
    parser.add_argument("--command-frame-seconds", type=float, default=0.5, help="Audio frame size while recording a command.")
    parser.add_argument("--command-start-timeout-seconds", type=float, default=5.0, help="Wait this long for speech after wake word.")
    parser.add_argument("--command-end-silence-seconds", type=float, default=1.0, help="Stop command recording after this much silence.")
    parser.add_argument("--command-max-seconds", type=float, default=8.0, help="Maximum command recording length after speech starts.")
    parser.add_argument("--command-window-seconds", type=float, default=20.0, help="NLU wake window after hotword detection.")
    parser.add_argument("--speech-rms-threshold", type=float, default=0.04, help="RMS threshold for command speech detection.")
    parser.add_argument("--asr-model-dir", dest="model_dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--vad-dir", type=Path, default=DEFAULT_VAD_DIR)
    parser.add_argument("--asr-device", dest="infer_device", default="cuda:0", help="auto, cpu, cuda:0, ...")
    parser.add_argument("--language", default="en", help="auto, zh, en, yue, ja, ko.")
    parser.add_argument("--merge-vad", action="store_true")
    parser.add_argument("--no-itn", action="store_true")
    parser.add_argument("--keep-wavs", type=Path, default=None, help="Optional directory to keep chunk wavs.")
    parser.add_argument("--raw-asr-json", action="store_true", help="Print full ASR JSON before NLU.")
    parser.add_argument("--max-chunks", type=int, default=0, help="Stop after N chunks. Default: 0 means run forever.")
    parser.add_argument(
        "--command-output",
        type=Path,
        default=DEFAULT_COMMAND_PATH,
        help="Write accepted NLU commands here for the driving agent.",
    )
    parser.add_argument(
        "--no-command-output",
        action="store_true",
        help="Only print accepted commands; do not write the command handoff file.",
    )

    parser.add_argument("--nlu-model-dir", type=Path, default=DEFAULT_BGE_DIR)
    parser.add_argument("--nlu-device", default="cpu", help="auto, cpu, cuda:0, ...")
    parser.add_argument("--no-embedding", action="store_true", help="Disable BGE fallback and use rules only.")
    parser.add_argument(
        "--print-ignored",
        dest="print_ignored",
        action="store_true",
        default=True,
        help="Print NLU ignored results too. Enabled by default for microphone debugging.",
    )
    parser.add_argument(
        "--no-print-ignored",
        dest="print_ignored",
        action="store_false",
        help="Show accepted commands only.",
    )
    return parser.parse_args()


def extract_clean_text(asr_result: object) -> str:
    if not isinstance(asr_result, list):
        return ""
    texts = []
    for item in asr_result:
        if isinstance(item, dict):
            text = item.get("clean_text") or item.get("text") or ""
            if text:
                texts.append(str(text))
    return " ".join(texts).strip()


def rms_of_i16(audio_i16: np.ndarray) -> float:
    if audio_i16.size == 0:
        return 0.0
    audio_f32 = audio_i16.astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(np.square(audio_f32))))


def read_i16_frame(proc: subprocess.Popen, bytes_per_frame: int) -> bytes:
    assert proc.stdout is not None
    return proc.stdout.read(bytes_per_frame)


def write_temp_wav(audio_i16: np.ndarray, args: argparse.Namespace, prefix: str, chunk_id: int) -> Path:
    wav_dir = args.keep_wavs or Path(tempfile.gettempdir())
    wav_path = wav_dir / f"{prefix}_{int(time.time())}_{chunk_id:04d}.wav"
    sf.write(wav_path, audio_i16.reshape(-1, args.channels), args.sample_rate, subtype="PCM_16")
    return wav_path


def transcribe_audio(
    model: object,
    audio_i16: np.ndarray,
    args: argparse.Namespace,
    prefix: str,
    chunk_id: int,
) -> tuple[object, float]:
    wav_path = write_temp_wav(audio_i16, args, prefix, chunk_id)
    started = time.perf_counter()
    result = transcribe_chunk(model, wav_path, args)
    elapsed = time.perf_counter() - started
    if not args.keep_wavs:
        wav_path.unlink(missing_ok=True)
    return result, elapsed


def publish_command(result: object, args: argparse.Namespace) -> None:
    if args.no_command_output or not getattr(result, "accepted", False):
        return
    payload = write_command(result.to_dict(), args.command_output)
    print(
        "Wrote command: "
        f"{args.command_output} "
        f"seq={payload.get('sequence_id')} "
        f"intent={payload.get('intent')}"
    )


def record_command_audio(proc: subprocess.Popen, args: argparse.Namespace) -> tuple[np.ndarray | None, dict[str, float]]:
    bytes_per_sample = 2
    samples_per_frame = int(args.sample_rate * args.command_frame_seconds)
    bytes_per_frame = samples_per_frame * args.channels * bytes_per_sample

    frames: list[np.ndarray] = []
    speech_started = False
    speech_started_at: float | None = None
    silence_seconds = 0.0
    wait_started_at = time.monotonic()
    frame_count = 0
    peak_rms = 0.0

    while proc.poll() is None:
        raw = read_i16_frame(proc, bytes_per_frame)
        if len(raw) < bytes_per_frame:
            break

        frame_count += 1
        frame = np.frombuffer(raw, dtype="<i2").copy()
        rms = rms_of_i16(frame)
        peak_rms = max(peak_rms, rms)
        now = time.monotonic()

        if rms >= args.speech_rms_threshold:
            if not speech_started:
                speech_started = True
                speech_started_at = now
                print(f"Command speech detected rms={rms:.4f}.")
            silence_seconds = 0.0
            frames.append(frame)
        elif speech_started:
            frames.append(frame)
            silence_seconds += args.command_frame_seconds
            if silence_seconds >= args.command_end_silence_seconds:
                break
        elif now - wait_started_at >= args.command_start_timeout_seconds:
            break

        if speech_started_at is not None and now - speech_started_at >= args.command_max_seconds:
            break

    stats = {
        "frames": float(frame_count),
        "peak_rms": peak_rms,
        "seconds": frame_count * args.command_frame_seconds,
    }
    if not frames:
        return None, stats
    return np.concatenate(frames), stats


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    args = parse_args()
    if args.list_devices:
        list_arecord_devices()
        return 0

    if not args.model_dir.exists():
        raise FileNotFoundError(f"ASR model directory not found: {args.model_dir}")
    if not args.nlu_model_dir.exists() and not args.no_embedding:
        raise FileNotFoundError(f"NLU model directory not found: {args.nlu_model_dir}")
    if args.keep_wavs:
        args.keep_wavs.mkdir(parents=True, exist_ok=True)

    print("Loading ASR model...")
    asr_model = build_model(args)
    print("Loading NLU parser...")
    nlu = VoxDriveNLU(
        model_dir=args.nlu_model_dir,
        device=args.nlu_device,
        active_window_seconds=args.command_window_seconds,
        use_embedding=not args.no_embedding,
        allow_inline_wake_command=False,
    )
    print("Ready. English mode. First say 'command' or 'vox drive'. Then say the driving command after the prompt. Press Ctrl+C to stop.")

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
            raw = read_i16_frame(proc, bytes_per_chunk)
            if len(raw) < bytes_per_chunk:
                break

            audio_i16 = np.frombuffer(raw, dtype="<i2").copy()
            rms = rms_of_i16(audio_i16)

            chunk_id += 1
            if rms < args.rms_threshold:
                if args.print_ignored:
                    print(f"[{chunk_id:04d}] silence rms={rms:.4f}")
                if args.max_chunks and chunk_id >= args.max_chunks:
                    break
                continue

            asr_result, elapsed = transcribe_audio(
                asr_model, audio_i16, args, "voxdrive_wake", chunk_id
            )

            if args.raw_asr_json:
                print(json.dumps(asr_result, ensure_ascii=False, indent=2))

            text = extract_clean_text(asr_result)
            if not text:
                if args.print_ignored:
                    print(f"[{chunk_id:04d}] rms={rms:.4f} asr={elapsed:.2f}s empty")
                if args.max_chunks and chunk_id >= args.max_chunks:
                    break
                continue

            result = nlu.parse(text)
            should_print = (
                result.accepted
                or args.print_ignored
                or result.reason == "wake_word_only_waiting_for_command"
            )
            if should_print:
                payload = result.to_dict()
                print(f"[{chunk_id:04d}] rms={rms:.4f} asr={elapsed:.2f}s text={text}")
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                publish_command(result, args)
                if result.reason == "wake_word_only_waiting_for_command":
                    print("Recording command... speak now.")
                    command_audio, command_stats = record_command_audio(proc, args)
                    if command_audio is None:
                        print(
                            "No command speech captured "
                            f"(peak_rms={command_stats['peak_rms']:.4f}, "
                            f"waited={command_stats['seconds']:.1f}s)."
                        )
                    else:
                        command_asr, command_elapsed = transcribe_audio(
                            asr_model, command_audio, args, "voxdrive_command", chunk_id
                        )
                        if args.raw_asr_json:
                            print(json.dumps(command_asr, ensure_ascii=False, indent=2))
                        command_text = extract_clean_text(command_asr)
                        command_rms = rms_of_i16(command_audio)
                        if not command_text:
                            print(
                                f"[{chunk_id:04d}] command rms={command_rms:.4f} "
                                f"asr={command_elapsed:.2f}s empty"
                            )
                        else:
                            command_result = nlu.parse(command_text)
                            print(
                                f"[{chunk_id:04d}] command rms={command_rms:.4f} "
                                f"asr={command_elapsed:.2f}s text={command_text}"
                            )
                            print(json.dumps(command_result.to_dict(), ensure_ascii=False, indent=2))
                            publish_command(command_result, args)

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
