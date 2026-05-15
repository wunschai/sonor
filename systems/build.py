"""BuildSystem — drives BuilderShip state machines and building construction."""
from __future__ import annotations
import pygame

from entities.ship import BuilderShip
from entities.building import Mothership, MiningStation, Turret
from entities.asteroid import Asteroid
from constants import (
    STATION_BUILD_TIME, STATION_ATTACH_RADIUS,
    TURRET_BUILD_TIME,
)

_ARRIVE_DIST = 20.0

# Map building_type string → (class, build_time)
_BUILD_TABLE: dict[str, tuple] = {
    "MiningStation": (MiningStation, STATION_BUILD_TIME),
    "Turret":        (Turret,        TURRET_BUILD_TIME),
}


class BuildSystem:
    """Updates all BuilderShip state machines and completes construction."""

    def update(self, world, dt: float) -> None:
        builders = [e for e in world.entities if isinstance(e, BuilderShip)]

        for b in builders:
            # Dead builder — reset progress, do nothing
            if not b.alive:
                b._build_progress = 0.0
                continue

            if b.state == "IDLE":
                pass   # waiting for assignment

            elif b.state == "MOVING_TO_SITE":
                if b.assigned_target is None:
                    b.state = "IDLE"
                    continue
                self._move_toward(b, b.assigned_target, dt)
                if self._arrived(b.pos, b.assigned_target):
                    b.state = "BUILDING"
                    b._build_progress = 0.0

            elif b.state == "BUILDING":
                if b.assigned_target is None or b.building_type is None:
                    b.state = "IDLE"
                    continue
                build_time = _BUILD_TABLE.get(b.building_type, (None, 30))[1]
                b._build_progress += dt
                if b._build_progress >= build_time:
                    self._complete(b, world)

            elif b.state == "WAITING_RESOURCES":
                pass   # future: check world.resources

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _arrived(pos_a: pygame.Vector2, pos_b: pygame.Vector2) -> bool:
        return pos_a.distance_to(pos_b) <= _ARRIVE_DIST

    @staticmethod
    def _move_toward(ship: BuilderShip, target: pygame.Vector2, dt: float) -> None:
        direction = target - ship.pos
        dist = direction.length()
        if dist < 1e-6:
            return
        spd = (ship.speed_mode.effective_speed(ship.speed)
               if hasattr(ship, "speed_mode") else ship.speed)
        step = spd * dt
        if step >= dist:
            ship.pos = pygame.Vector2(target)
        else:
            ship.pos += direction.normalize() * step

    @staticmethod
    def _complete(builder: BuilderShip, world) -> None:
        """Instantiate the building, auto-attach to nearby asteroid, add to world."""
        entry = _BUILD_TABLE.get(builder.building_type)
        if entry is None:
            return
        klass, _ = entry
        new_entity = klass(pos=builder.pos, team=builder.team)

        # Auto-attach MiningStation to nearest asteroid within range
        if isinstance(new_entity, MiningStation):
            asteroids = world.asteroids
            nearest = None
            nearest_dist = STATION_ATTACH_RADIUS + 1
            for ast in asteroids:
                d = new_entity.pos.distance_to(ast.pos)
                if d <= STATION_ATTACH_RADIUS and d < nearest_dist:
                    nearest_dist = d
                    nearest = ast
            new_entity.attached_asteroid = nearest

        world.add_entity(new_entity)

        # Reset builder
        builder._build_progress = 0.0
        builder.building_type = None
        builder.assigned_target = None
        builder._building_entity = None
        builder.state = "IDLE"
