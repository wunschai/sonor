"""Active and passive sonar mechanics."""
from __future__ import annotations
import random
import math
from dataclasses import dataclass, field
from typing import List

from constants import (
    PULSE_SPEED, PULSE_DECAY_DIST,
    PASSIVE_RADIUS, PASSIVE_NOISE, PASSIVE_FADE,
    PASSIVE_VOL_L1, PASSIVE_VOL_L2, SIZE_FACTORS,
    TEAM_PLAYER,
)


@dataclass
class SonarHit:
    """A detected contact returned by active or passive sonar."""
    world_pos: tuple          # (x, y) — may include noise for passive
    intensity: int            # 1, 2, or 3
    source: str               # "active" or "passive"
    fade_timer: float = field(default=0.0)   # counts up; caller compares to fade limit


# ── Active Pulse ──────────────────────────────────────────────────

class ActivePulse:
    """Expanding ring fired by a ship's active sonar."""

    # Tolerance: entity counts as hit if dist is within this many px of radius
    _HIT_TOLERANCE = 30.0

    def __init__(self, *, origin: tuple, strength: int):
        self.origin   = tuple(origin)
        self.strength = strength
        self.radius   = 0.0
        self._decay_milestone = PULSE_DECAY_DIST  # next decay threshold

    def update(self, dt: float) -> bool:
        """Advance the pulse. Returns True while alive, False when dead."""
        self.radius += PULSE_SPEED * dt

        # Decay one level each time we cross another PULSE_DECAY_DIST boundary
        while self.radius >= self._decay_milestone:
            self.strength -= 1
            self._decay_milestone += PULSE_DECAY_DIST
            if self.strength <= 0:
                return False

        return True

    def check_hit(self, entities: list) -> List[SonarHit]:
        """Return SonarHit for each entity whose distance from origin ≈ radius."""
        hits: List[SonarHit] = []
        ox, oy = self.origin
        for entity in entities:
            ex, ey = float(entity.pos.x), float(entity.pos.y)
            dist = math.hypot(ex - ox, ey - oy)
            if abs(dist - self.radius) <= self._HIT_TOLERANCE:
                size   = getattr(entity, "size", "S")
                factor = SIZE_FACTORS.get(size, 1)
                intensity = min(self.strength, factor)
                hits.append(SonarHit(
                    world_pos=(ex, ey),
                    intensity=intensity,
                    source="active",
                ))
        return hits


# ── Passive Detector ─────────────────────────────────────────────

class PassiveDetector:
    """Detects nearby moving enemies based on their noise signature."""

    def __init__(self):
        self._timer = 0.0
        self._interval = 1.5

    def detect(self, viewers: list, enemies: list, dt: float = 0.0) -> List[SonarHit]:
        """
        viewers — player units whose position is used as the listening centre.
        enemies — candidate units to detect (non-player checked automatically).
        dt — time delta; when non-zero, gating timer is applied (1.5 s interval).
        Returns list of SonarHit, one per viewer-enemy pair that triggers.
        """
        if dt > 0.0:
            self._timer += dt
            if self._timer < self._interval:
                return []
            self._timer -= self._interval

        hits: List[SonarHit] = []

        for viewer in viewers:
            vx, vy = float(viewer.pos.x), float(viewer.pos.y)

            for enemy in enemies:
                # Only detect non-player units
                if getattr(enemy, "team", None) == TEAM_PLAYER:
                    continue

                # Must be within passive radius
                ex, ey = float(enemy.pos.x), float(enemy.pos.y)
                dist = math.hypot(ex - vx, ey - vy)
                if dist > PASSIVE_RADIUS:
                    continue

                # Noise volume = speed × size factor
                if hasattr(enemy, "speed_mode"):
                    speed = enemy.speed_mode.effective_speed(enemy.speed)
                else:
                    speed = getattr(enemy, "speed", 0.0)
                size   = getattr(enemy, "size", "S")
                factor = SIZE_FACTORS.get(size, 1)
                volume = speed * factor

                if volume <= 0:
                    continue

                # Map volume to intensity level
                if volume < PASSIVE_VOL_L1:
                    intensity = 1
                elif volume < PASSIVE_VOL_L2:
                    intensity = 2
                else:
                    intensity = 3

                # Add position noise
                nx = ex + random.uniform(-PASSIVE_NOISE, PASSIVE_NOISE)
                ny = ey + random.uniform(-PASSIVE_NOISE, PASSIVE_NOISE)

                hits.append(SonarHit(
                    world_pos=(nx, ny),
                    intensity=intensity,
                    source="passive",
                ))

        return hits
