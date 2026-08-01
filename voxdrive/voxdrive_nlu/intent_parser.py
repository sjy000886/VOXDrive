"""ASR text to canonical LMDrive instruction parser."""

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

from .canonical_instructions import (
    EMERGENCY_BYPASS_PHRASES,
    INTENT_SPECS,
    WAKE_WORDS,
    IntentSpec,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BGE_DIR = REPO_ROOT / "ckpts" / "bge-small-zh-v1.5"

_PUNCT_RE = re.compile(r"[\s,，。.!！?？;；:：]+")
_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")
_CHINESE_NUMBER_RE = re.compile(r"[零〇一二两三四五六七八九十百]+")
_CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}


@dataclass
class NLUResult:
    accepted: bool
    reason: str
    raw_text: str
    command_text: str = ""
    intent: Optional[str] = None
    canonical_lmdrive_instruction: Optional[str] = None
    mode: Optional[str] = None
    speed_limit_kmh: Optional[float] = None
    distance_m: Optional[float] = None
    external_control: Dict[str, object] = field(default_factory=dict)
    confidence: float = 0.0
    source: str = "none"

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class VoxDriveNLU:
    """Parse noisy ASR text into conservative LMDrive-compatible commands."""

    def __init__(
        self,
        model_dir: Path = DEFAULT_BGE_DIR,
        device: str = "auto",
        active_window_seconds: float = 5.0,
        cooldown_seconds: float = 0.8,
        min_similarity: float = 0.62,
        use_embedding: bool = True,
        allow_emergency_without_wake: bool = True,
        allow_inline_wake_command: bool = False,
    ):
        self.model_dir = Path(model_dir)
        self.device = self._resolve_device(device)
        self.active_window_seconds = active_window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.min_similarity = min_similarity
        self.use_embedding = use_embedding
        self.allow_emergency_without_wake = allow_emergency_without_wake
        self.allow_inline_wake_command = allow_inline_wake_command

        self.active_until = 0.0
        self.last_accepted_at = 0.0
        self.last_signature = ""

        self._tokenizer = None
        self._model = None
        self._example_texts = []
        self._example_specs = []
        self._example_embeddings = None

    def parse(self, text: str, now: Optional[float] = None) -> NLUResult:
        now = time.monotonic() if now is None else now
        raw_text = text or ""
        normalized = self.normalize(raw_text)
        if not normalized:
            return NLUResult(False, "empty_text", raw_text)

        if self.allow_emergency_without_wake and self._has_emergency_bypass(normalized):
            result = self._build_result(
                "EMERGENCY_STOP",
                raw_text,
                normalized,
                confidence=1.0,
                source="emergency_bypass",
            )
            self._mark_accepted(result, now)
            return result

        wake_found, command_text = self._strip_wake_word(normalized)
        if wake_found:
            self.active_until = now + self.active_window_seconds
            if not self.allow_inline_wake_command:
                return NLUResult(False, "wake_word_only_waiting_for_command", raw_text)
            if not command_text:
                return NLUResult(False, "wake_word_only_waiting_for_command", raw_text)
        elif now <= self.active_until:
            command_text = normalized
        else:
            return NLUResult(False, "missing_wake_word", raw_text)

        if self._is_in_cooldown(command_text, now):
            return NLUResult(False, "cooldown_duplicate", raw_text, command_text)

        result = self._parse_command(raw_text, command_text)
        if result.accepted:
            self.active_until = 0.0
            self._mark_accepted(result, now)
        return result

    def normalize(self, text: str) -> str:
        normalized = text.strip().lower()
        normalized = _PUNCT_RE.sub(" ", normalized)
        return " ".join(normalized.split())

    def _parse_command(self, raw_text: str, command_text: str) -> NLUResult:
        rule_result = self._parse_by_rules(raw_text, command_text)
        if rule_result is not None:
            return rule_result

        if not self.use_embedding:
            return NLUResult(False, "no_intent_matched", raw_text, command_text)

        intent_name, score = self._match_by_embedding(command_text)
        if intent_name is None or score < self.min_similarity:
            return NLUResult(
                False,
                "low_similarity",
                raw_text,
                command_text,
                confidence=score,
                source="embedding",
            )
        return self._build_result(
            intent_name,
            raw_text,
            command_text,
            confidence=score,
            source="embedding",
        )

    def _parse_by_rules(self, raw_text: str, command_text: str) -> Optional[NLUResult]:
        text = command_text

        speed = self._extract_speed_kmh(text)
        if speed is not None:
            return NLUResult(
                True,
                "matched_speed_limit",
                raw_text,
                command_text,
                intent="SET_SPEED",
                canonical_lmdrive_instruction="Proceed along this route.",
                mode="AUTONOMOUS",
                speed_limit_kmh=speed,
                external_control={"speed_limit_kmh": speed},
                confidence=1.0,
                source="rule",
            )

        distance = self._extract_distance_m(text)
        if distance is not None and self._has_left(text) and self._has_turn(text):
            return NLUResult(
                True,
                "matched_left_after_distance",
                raw_text,
                command_text,
                intent="TURN_LEFT_AFTER_DISTANCE",
                canonical_lmdrive_instruction="After %.0f meters, take a left." % distance,
                mode="AUTONOMOUS",
                distance_m=distance,
                confidence=1.0,
                source="rule",
            )
        if distance is not None and self._has_right(text) and self._has_turn(text):
            return NLUResult(
                True,
                "matched_right_after_distance",
                raw_text,
                command_text,
                intent="TURN_RIGHT_AFTER_DISTANCE",
                canonical_lmdrive_instruction="After %.0f meters, take a right." % distance,
                mode="AUTONOMOUS",
                distance_m=distance,
                confidence=1.0,
                source="rule",
            )

        if self._has_stop(text):
            return self._build_result("STOP", raw_text, command_text, 1.0, "rule")
        if self._has_start(text):
            return self._build_result("START", raw_text, command_text, 1.0, "rule")
        if self._has_lane_change(text) and self._has_left(text):
            return self._build_result("CHANGE_LEFT", raw_text, command_text, 1.0, "rule")
        if self._has_lane_change(text) and self._has_right(text):
            return self._build_result("CHANGE_RIGHT", raw_text, command_text, 1.0, "rule")
        if self._has_left(text) and self._has_turn(text):
            return self._build_result("TURN_LEFT_NEXT", raw_text, command_text, 1.0, "rule")
        if self._has_right(text) and self._has_turn(text):
            return self._build_result("TURN_RIGHT_NEXT", raw_text, command_text, 1.0, "rule")
        if self._has_accelerate(text):
            return self._build_result("ACCELERATE", raw_text, command_text, 1.0, "rule")
        if self._has_slow_down(text):
            return self._build_result("SLOW_DOWN", raw_text, command_text, 1.0, "rule")
        if self._has_straight(text):
            return self._build_result("KEEP_STRAIGHT", raw_text, command_text, 1.0, "rule")
        if self._has_continue(text):
            return self._build_result("CONTINUE_ROUTE", raw_text, command_text, 1.0, "rule")

        return None

    def _build_result(
        self,
        intent_name: str,
        raw_text: str,
        command_text: str,
        confidence: float,
        source: str,
    ) -> NLUResult:
        spec = self._get_spec(intent_name)
        external_control = {}
        if spec.external_action == "FULL_BRAKE":
            external_control = {"throttle": 0.0, "brake": 1.0}
        elif spec.external_action == "SLOW_DOWN":
            external_control = {"speed_delta_kmh": -10.0}
        elif spec.external_action == "SPEED_UP":
            external_control = {"speed_delta_kmh": 10.0}
        return NLUResult(
            True,
            "matched_intent",
            raw_text,
            command_text,
            intent=spec.name,
            canonical_lmdrive_instruction=spec.lm_instruction,
            mode=spec.mode,
            external_control=external_control,
            confidence=float(confidence),
            source=source,
        )

    def _strip_wake_word(self, text: str) -> Tuple[bool, str]:
        for wake in sorted(WAKE_WORDS, key=len, reverse=True):
            idx = text.find(wake)
            if idx < 0:
                continue
            after = text[idx + len(wake) :].strip()
            before = text[:idx].strip()
            if after:
                return True, after
            return True, before
        return False, text

    def _has_emergency_bypass(self, text: str) -> bool:
        return any(phrase in text for phrase in EMERGENCY_BYPASS_PHRASES)

    def _is_in_cooldown(self, command_text: str, now: float) -> bool:
        return (
            command_text == self.last_signature
            and now - self.last_accepted_at < self.cooldown_seconds
        )

    def _mark_accepted(self, result: NLUResult, now: float) -> None:
        self.last_accepted_at = now
        self.last_signature = result.command_text

    def _match_by_embedding(self, text: str) -> Tuple[Optional[str], float]:
        self._ensure_embedding_model()
        query = self._encode([text])
        scores = torch.matmul(query, self._example_embeddings.T).squeeze(0)
        best_idx = int(torch.argmax(scores).item())
        return self._example_specs[best_idx].name, float(scores[best_idx].item())

    def _ensure_embedding_model(self) -> None:
        if self._model is not None:
            return
        if not self.model_dir.exists():
            raise FileNotFoundError(
                "BGE model directory not found: %s" % self.model_dir
            )
        self._tokenizer = AutoTokenizer.from_pretrained(
            str(self.model_dir), local_files_only=True
        )
        self._model = AutoModel.from_pretrained(
            str(self.model_dir), local_files_only=True
        ).to(self.device)
        self._model.eval()

        self._example_texts = []
        self._example_specs = []
        for spec in INTENT_SPECS:
            for example in spec.examples:
                self._example_texts.append(example)
                self._example_specs.append(spec)
        self._example_embeddings = self._encode(self._example_texts)

    def _encode(self, texts: Sequence[str]) -> torch.Tensor:
        assert self._tokenizer is not None
        assert self._model is not None
        encoded = self._tokenizer(
            list(texts),
            padding=True,
            truncation=True,
            max_length=64,
            return_tensors="pt",
        ).to(self.device)
        with torch.no_grad():
            output = self._model(**encoded)
            embeddings = output.last_hidden_state[:, 0]
            embeddings = F.normalize(embeddings, p=2, dim=1)
        return embeddings

    def _resolve_device(self, device: str) -> str:
        if device == "auto":
            return "cuda:0" if torch.cuda.is_available() else "cpu"
        return device

    def _get_spec(self, intent_name: str) -> IntentSpec:
        for spec in INTENT_SPECS:
            if spec.name == intent_name:
                return spec
        raise KeyError("Unknown intent: %s" % intent_name)

    def _extract_speed_kmh(self, text: str) -> Optional[float]:
        if not any(
            key in text
            for key in (
                "km/h",
                "kph",
                "kilometer per hour",
                "kilometers per hour",
                "kilometre per hour",
                "kilometres per hour",
                "speed",
                "accelerate",
                "decelerate",
                "公里",
                "千米每小时",
                "速度",
                "提速",
                "减速",
            )
        ):
            return None
        return self._extract_number(text)

    def _extract_distance_m(self, text: str) -> Optional[float]:
        if not any(key in text for key in ("meter", "meters", "metre", "metres", "米", "m ")):
            return None
        return self._extract_number(text)

    def _extract_number(self, text: str) -> Optional[float]:
        match = _NUMBER_RE.search(text)
        if match is not None:
            return float(match.group(1))
        chinese_match = _CHINESE_NUMBER_RE.search(text)
        if chinese_match is not None:
            value = 0
            digit = 0
            for char in chinese_match.group(0):
                if char in _CHINESE_DIGITS:
                    digit = _CHINESE_DIGITS[char]
                elif char == "十":
                    value += max(digit, 1) * 10
                    digit = 0
                elif char == "百":
                    value += max(digit, 1) * 100
                    digit = 0
            return float(value + digit)
        words = text.split()
        total = 0
        current = 0
        matched = False
        for word in words:
            if word not in _NUMBER_WORDS:
                if matched:
                    break
                continue
            matched = True
            value = _NUMBER_WORDS[word]
            if value == 100:
                current = max(current, 1) * 100
            else:
                current += value
        total += current
        return float(total) if matched else None

    def _has_left(self, text: str) -> bool:
        return "left" in text or "左" in text

    def _has_right(self, text: str) -> bool:
        return "right" in text or "右" in text

    def _has_turn(self, text: str) -> bool:
        return any(key in text for key in ("turn", "转", "路口", "junction", "intersection"))

    def _has_lane_change(self, text: str) -> bool:
        return any(key in text for key in ("lane", "变道", "并道", "车道", "switch", "change"))

    def _has_stop(self, text: str) -> bool:
        return any(key in text for key in ("stop", "halt", "停车", "停下", "刹车"))

    def _has_start(self, text: str) -> bool:
        return any(
            key in text
            for key in ("start", "go ahead", "drive", "启动", "开始", "出发", "往前开")
        )

    def _has_slow_down(self, text: str) -> bool:
        return any(key in text for key in ("slow", "decelerate", "减速", "慢一点", "安全车速"))

    def _has_accelerate(self, text: str) -> bool:
        return any(key in text for key in ("accelerate", "speed up", "faster", "加速", "快一点", "提速"))

    def _has_straight(self, text: str) -> bool:
        return any(key in text for key in ("straight", "直行", "当前方向", "当前车道"))

    def _has_continue(self, text: str) -> bool:
        return any(key in text for key in ("continue", "keep going", "接着", "继续", "沿当前路线"))
