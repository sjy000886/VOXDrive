"""State tracking for voice-requested navigation maneuvers.

The controller only selects MindDrive's existing high-level navigation command.
MindDrive remains responsible for producing the trajectory and low-level control.
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Sequence


VOICE_COMMAND_IDS = {
    "TURN_LEFT_NEXT": 1,
    "TURN_LEFT_AFTER_DISTANCE": 1,
    "TURN_RIGHT_NEXT": 2,
    "TURN_RIGHT_AFTER_DISTANCE": 2,
    "CHANGE_LEFT": 5,
    "CHANGE_RIGHT": 6,
}

LANE_CHANGE_INTENTS = {"CHANGE_LEFT", "CHANGE_RIGHT"}
TURN_INTENTS = {
    "TURN_LEFT_NEXT",
    "TURN_LEFT_AFTER_DISTANCE",
    "TURN_RIGHT_NEXT",
    "TURN_RIGHT_AFTER_DISTANCE",
}


def _heading_error(current: float, reference: float) -> float:
    return (current - reference + math.pi) % (2.0 * math.pi) - math.pi


class VoiceManeuverController:
    """Keep voice navigation commands active long enough to finish safely.

    Lane changes are followed by a lane-follow settling phase.  This makes the
    learned planner generate the counter-steer/centering portion of the lane
    change instead of leaving the last steering request active indefinitely.
    """

    def __init__(
        self,
        lane_change_max_distance_m: float = 18.0,
        lane_change_settle_distance_m: float = 8.0,
        turn_max_distance_m: float = 45.0,
        turn_settle_distance_m: float = 10.0,
    ) -> None:
        self.lane_change_max_distance_m = lane_change_max_distance_m
        self.lane_change_settle_distance_m = lane_change_settle_distance_m
        self.turn_max_distance_m = turn_max_distance_m
        self.turn_settle_distance_m = turn_settle_distance_m
        self.cancel()

    def cancel(self) -> None:
        self.intent: Optional[str] = None
        self.phase = "idle"
        self.command_id: Optional[int] = None
        self.delay_remaining_m = 0.0
        self.phase_distance_m = 0.0
        self.max_heading_delta_rad = 0.0
        self.start_heading: Optional[float] = None
        self.last_position: Optional[tuple[float, float]] = None
        self.just_completed = False

    def submit(
        self,
        intent: str,
        position: Sequence[float],
        heading: float,
        delay_distance_m: float = 0.0,
    ) -> bool:
        if intent not in VOICE_COMMAND_IDS:
            return False
        self.intent = intent
        self.command_id = VOICE_COMMAND_IDS[intent]
        self.phase = "waiting" if delay_distance_m > 0.0 else "active"
        self.delay_remaining_m = max(0.0, float(delay_distance_m))
        self.phase_distance_m = 0.0
        self.max_heading_delta_rad = 0.0
        self.start_heading = float(heading)
        self.last_position = self._position(position)
        self.just_completed = False
        return True

    def update(self, position: Sequence[float], heading: float) -> Optional[int]:
        self.just_completed = False
        if self.phase == "idle":
            return None

        current_position = self._position(position)
        segment_distance = self._segment_distance(current_position)
        self.last_position = current_position

        if self.phase == "waiting":
            self.delay_remaining_m -= segment_distance
            if self.delay_remaining_m > 0.0:
                return None
            self.phase = "active"
            self.phase_distance_m = 0.0
            self.start_heading = float(heading)
            self.max_heading_delta_rad = 0.0
            return self.command_id

        self.phase_distance_m += segment_distance
        if self.phase == "active":
            heading_delta = abs(_heading_error(float(heading), float(self.start_heading)))
            self.max_heading_delta_rad = max(self.max_heading_delta_rad, heading_delta)
            if self._active_phase_finished(heading_delta):
                self.phase = "settling"
                self.phase_distance_m = 0.0
                # Command 4 is MindDrive's LANEFOLLOW instruction.  Keeping it
                # active here produces the counter-steer and wheel centering.
                return 4
            return self.command_id

        if self.phase == "settling":
            settle_distance = (
                self.lane_change_settle_distance_m
                if self.intent in LANE_CHANGE_INTENTS
                else self.turn_settle_distance_m
            )
            if self.phase_distance_m >= settle_distance:
                self.cancel()
                self.just_completed = True
                return None
            return 4

        return None

    def snapshot(self) -> Dict[str, object]:
        return {
            "intent": self.intent,
            "phase": self.phase,
            "command_id": self.command_id,
            "delay_remaining_m": round(self.delay_remaining_m, 3),
            "phase_distance_m": round(self.phase_distance_m, 3),
            "max_heading_delta_deg": round(math.degrees(self.max_heading_delta_rad), 3),
            "just_completed": self.just_completed,
        }

    def _active_phase_finished(self, heading_delta: float) -> bool:
        if self.intent in LANE_CHANGE_INTENTS:
            changed_heading = self.max_heading_delta_rad >= math.radians(4.0)
            heading_recovered = heading_delta <= math.radians(1.5)
            learned_lane_change_finished = (
                self.phase_distance_m >= 6.0 and changed_heading and heading_recovered
            )
            return (
                learned_lane_change_finished
                or self.phase_distance_m >= self.lane_change_max_distance_m
            )
        if self.intent in TURN_INTENTS:
            return (
                self.max_heading_delta_rad >= math.radians(50.0)
                or self.phase_distance_m >= self.turn_max_distance_m
            )
        return True

    def _segment_distance(self, current: tuple[float, float]) -> float:
        if self.last_position is None:
            return 0.0
        distance = math.hypot(
            current[0] - self.last_position[0],
            current[1] - self.last_position[1],
        )
        # A GPS reset/teleport between scenarios must not finish a maneuver.
        return distance if distance <= 10.0 else 0.0

    @staticmethod
    def _position(position: Sequence[float]) -> tuple[float, float]:
        return float(position[0]), float(position[1])
