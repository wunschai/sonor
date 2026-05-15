"""Soft separation for idle ships, and formation offset helpers for move orders."""
import math
import pygame

from entities.ship import CombatShip, MiningShip, BuilderShip
from entities.building import Mothership, MiningStation, Turret

_RADII = {"S": 8, "M": 12, "L": 18, "X": 6}
_BUILDINGS = (Mothership, MiningStation, Turret)


def _radius(entity) -> float:
    return _RADII.get(getattr(entity, "size", "S"), 8)


def _is_idle(entity) -> bool:
    """True when the ship is not pursuing any goal and should be nudged apart."""
    if isinstance(entity, (MiningShip, BuilderShip)):
        return getattr(entity, "state", "") == "IDLE"
    if isinstance(entity, CombatShip):
        return getattr(entity, "_target_pos", None) is None
    return False


def formation_offsets(n: int, spacing: float = 28.0) -> list:
    """Return n pygame.Vector2 offsets arranged in a compact grid centred on (0,0)."""
    if n <= 0:
        return []
    cols = max(1, round(math.sqrt(n)))
    offsets = []
    for i in range(n):
        row, col = divmod(i, cols)
        x = (col - (cols - 1) / 2.0) * spacing
        y = (row - 0) * spacing
        offsets.append(pygame.Vector2(x, y))
    return offsets


def resolve_separation(world) -> None:
    """Gently push overlapping idle ships apart from buildings and each other.

    Ships that are moving, mining, or building are left alone so their
    state machines are not disrupted.
    """
    idle_ships = [
        e for e in world.entities
        if isinstance(e, (CombatShip, MiningShip, BuilderShip)) and _is_idle(e)
    ]
    if not idle_ships:
        return

    buildings = [e for e in world.entities if isinstance(e, _BUILDINGS)]
    obstacles = idle_ships + buildings

    displacements: dict[int, pygame.Vector2] = {
        id(s): pygame.Vector2(0, 0) for s in idle_ships
    }

    for ship in idle_ships:
        r1 = _radius(ship)
        for other in obstacles:
            if other is ship:
                continue
            delta = ship.pos - other.pos
            dist = delta.length()
            min_dist = r1 + _radius(other)
            if dist == 0:
                displacements[id(ship)] += pygame.Vector2(r1, 0)
            elif dist < min_dist:
                displacements[id(ship)] += delta.normalize() * (min_dist - dist)

    for ship in idle_ships:
        ship.pos += displacements[id(ship)]
