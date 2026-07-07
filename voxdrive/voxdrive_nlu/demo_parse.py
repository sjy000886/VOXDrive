"""Right-click runnable demo for VoxDrive NLU."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from voxdrive.voxdrive_nlu.intent_parser import DEFAULT_BGE_DIR, VoxDriveNLU


SAMPLES = [
    "今天天气不错，往前开",
    "command go ahead",
    "command 出发吧",
    "小沃，前方路口左转",
    "voxdrive change to the right lane",
    "command speed to 5 km/h",
    "command 前方300米右转",
    "急停",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test ASR text to LMDrive command parsing.")
    parser.add_argument("texts", nargs="*", help="ASR text samples to parse.")
    parser.add_argument(
        "--model-dir",
        default=str(DEFAULT_BGE_DIR),
        help="Local BGE model directory.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="Embedding device: auto, cpu, cuda:0.",
    )
    parser.add_argument(
        "--no-embedding",
        action="store_true",
        help="Disable BGE fallback and use rules only.",
    )
    parser.add_argument(
        "--allow-inline-wake-command",
        action="store_true",
        help="Allow 'command go ahead' as a single utterance. Default is strict two-stage mode.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    texts = args.texts or SAMPLES
    nlu = VoxDriveNLU(
        model_dir=Path(args.model_dir),
        device=args.device,
        use_embedding=not args.no_embedding,
        allow_inline_wake_command=args.allow_inline_wake_command,
    )

    for text in texts:
        result = nlu.parse(text)
        print("=" * 80)
        print("ASR:", text)
        print(result.to_json())


if __name__ == "__main__":
    main()
