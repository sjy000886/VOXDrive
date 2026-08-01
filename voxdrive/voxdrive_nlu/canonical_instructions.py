"""Canonical intent definitions for mapping ASR text to LMDrive inputs."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class IntentSpec:
    name: str
    lm_instruction: Optional[str]
    mode: Optional[str]
    external_action: Optional[str]
    examples: Tuple[str, ...]


WAKE_WORDS = (
    "command",
    "commands",
    "comman",
    "common",
    "com man",
    "com慢",
    "voxdrive",
    "vox drive",
    "hey voxdrive",
    "hey vox drive",
    "box drive",
    "fox drive",
    "voice drive",
    "vox dry",
    "小沃",
    "小我",
    "小窝",
    "小喔",
    "晓沃",
    "小vo",
    "小 v",
    "命令",
    "语音指令",
)

# Emergency wake bypass is intentionally narrow. Ordinary "stop" still needs
# the wake word, but explicit emergency phrases are accepted immediately.
EMERGENCY_BYPASS_PHRASES = (
    "emergency stop",
    "brake now",
    "急停",
    "紧急刹车",
    "紧急停车",
)


INTENT_SPECS = (
    IntentSpec(
        name="START",
        lm_instruction="Please commence driving.",
        mode="AUTONOMOUS",
        external_action=None,
        examples=(
            "start driving",
            "go ahead",
            "move on",
            "let's go",
            "开始驾驶",
            "启动",
            "出发",
            "往前开",
        ),
    ),
    IntentSpec(
        name="CONTINUE_ROUTE",
        lm_instruction="Proceed along this route.",
        mode="AUTONOMOUS",
        external_action=None,
        examples=(
            "continue",
            "keep going",
            "follow this route",
            "proceed along this road",
            "继续开",
            "接着开",
            "沿当前路线行驶",
            "继续往前",
        ),
    ),
    IntentSpec(
        name="KEEP_STRAIGHT",
        lm_instruction="Maintain your current course.",
        mode="AUTONOMOUS",
        external_action=None,
        examples=(
            "go straight",
            "keep straight",
            "maintain current course",
            "直行",
            "保持直行",
            "保持当前方向",
        ),
    ),
    IntentSpec(
        name="TURN_LEFT_NEXT",
        lm_instruction="Please execute a left turn at the forthcoming intersection.",
        mode="AUTONOMOUS",
        external_action=None,
        examples=(
            "turn left at the next intersection",
            "take a left at the next junction",
            "next intersection turn left",
            "下个路口左转",
            "前方路口左转",
            "路口左转",
        ),
    ),
    IntentSpec(
        name="TURN_RIGHT_NEXT",
        lm_instruction="Please execute a right turn at the upcoming intersection.",
        mode="AUTONOMOUS",
        external_action=None,
        examples=(
            "turn right at the next intersection",
            "take a right at the next junction",
            "next intersection turn right",
            "下个路口右转",
            "前方路口右转",
            "路口右转",
        ),
    ),
    IntentSpec(
        name="CHANGE_LEFT",
        lm_instruction="Transition to the left lane for travel.",
        mode="AUTONOMOUS",
        external_action=None,
        examples=(
            "change to the left lane",
            "switch to left lane",
            "move to the left lane",
            "向左变道",
            "切到左侧车道",
            "左侧并道",
        ),
    ),
    IntentSpec(
        name="CHANGE_RIGHT",
        lm_instruction="Transition to the right lane for travel.",
        mode="AUTONOMOUS",
        external_action=None,
        examples=(
            "change to the right lane",
            "switch to right lane",
            "move to the right lane",
            "向右变道",
            "切到右侧车道",
            "右侧并道",
        ),
    ),
    IntentSpec(
        name="ACCELERATE",
        lm_instruction="Please increase the driving speed.",
        mode="AUTONOMOUS",
        external_action="SPEED_UP",
        examples=(
            "accelerate",
            "speed up",
            "go faster",
            "加速",
            "快一点",
            "提速",
        ),
    ),
    IntentSpec(
        name="SLOW_DOWN",
        lm_instruction="Please decelerate immediately.",
        mode="AUTONOMOUS",
        external_action="SLOW_DOWN",
        examples=(
            "slow down",
            "decelerate",
            "keep a safe speed",
            "减速",
            "慢一点",
            "保持安全车速",
        ),
    ),
    IntentSpec(
        name="STOP",
        lm_instruction=None,
        mode="STOPPED",
        external_action="FULL_BRAKE",
        examples=(
            "stop",
            "halt",
            "brake",
            "pull over and stop",
            "停车",
            "停下",
            "刹车",
        ),
    ),
    IntentSpec(
        name="EMERGENCY_STOP",
        lm_instruction=None,
        mode="STOPPED",
        external_action="FULL_BRAKE",
        examples=EMERGENCY_BYPASS_PHRASES,
    ),
)
