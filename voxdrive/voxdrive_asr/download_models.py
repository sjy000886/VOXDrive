#!/usr/bin/env python
"""Download VoxDrive ASR models into ./ckpts/<model_name>."""

from __future__ import annotations

import argparse
from pathlib import Path

from modelscope.hub.snapshot_download import snapshot_download


MODEL_REGISTRY = {
    "SenseVoiceSmall": "iic/SenseVoiceSmall",
    "fsmn-vad": "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "ct-punc": "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
    "paraformer-zh-streaming": "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online",
}


def download_model(name: str, ckpt_root: Path) -> Path:
    if name not in MODEL_REGISTRY:
        known = ", ".join(sorted(MODEL_REGISTRY))
        raise ValueError(f"Unknown model '{name}'. Known models: {known}")

    target_dir = ckpt_root / name
    target_dir.mkdir(parents=True, exist_ok=True)
    model_id = MODEL_REGISTRY[name]

    print(f"Downloading {model_id} -> {target_dir}")
    resolved = snapshot_download(model_id, local_dir=str(target_dir))
    print(f"Ready: {resolved}")
    return Path(resolved)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "models",
        nargs="+",
        choices=sorted([*MODEL_REGISTRY.keys(), "all"]),
        help="Model names to download. Use 'all' for every registered model.",
    )
    parser.add_argument(
        "--ckpt-root",
        type=Path,
        default=Path("ckpts"),
        help="Root checkpoint directory. Default: ./ckpts",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ckpt_root = args.ckpt_root.resolve()
    names = list(MODEL_REGISTRY) if "all" in args.models else args.models

    for name in names:
        download_model(name, ckpt_root)


if __name__ == "__main__":
    main()
