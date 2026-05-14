"""Determines which entities should be drawn given the current fog state."""
from core.fog import FogMap
from entities.asteroid import Asteroid
from constants import TEAM_PLAYER


def should_draw_entity(entity, fog: FogMap) -> bool:
    """Return True if the entity should be rendered to the player."""
    # Player-owned units are always visible
    if hasattr(entity, "team") and entity.team == TEAM_PLAYER:
        return True

    # Revealed asteroids are always drawn (permanent marker)
    if isinstance(entity, Asteroid):
        if entity.revealed:
            return True
        # Unrevealed — only draw if currently in VISIBLE fog cell
        return fog.is_visible(entity.pos)

    # All other entities (enemy units, buildings) only shown when VISIBLE
    return fog.is_visible(entity.pos)
