import pygame
from constants import MAP_WIDTH, MAP_HEIGHT, TEAM_PLAYER, TEAM_ENEMY
from entities.asteroid import Asteroid


class World:
    """Central container for all game entities and game-state resources."""

    def __init__(self):
        self.width  = MAP_WIDTH
        self.height = MAP_HEIGHT
        self.entities: list = []
        self.resources = {TEAM_PLAYER: 0, TEAM_ENEMY: 0}

    # ── Entity management ─────────────────────────────────────────

    def add_entity(self, entity):
        if entity not in self.entities:
            self.entities.append(entity)

    def remove_entity(self, entity):
        if entity in self.entities:
            self.entities.remove(entity)

    # ── Filtered views ────────────────────────────────────────────

    def entities_for_team(self, team) -> list:
        return [e for e in self.entities
                if hasattr(e, "team") and e.team == team]

    @property
    def asteroids(self) -> list:
        return [e for e in self.entities if isinstance(e, Asteroid)]

    # ── Spatial query ─────────────────────────────────────────────

    def entities_in_radius(self, center, radius) -> list:
        cx, cy = center
        r2 = radius * radius
        result = []
        for e in self.entities:
            pos = e.pos
            dx = pos.x - cx
            dy = pos.y - cy
            if dx * dx + dy * dy <= r2:
                result.append(e)
        return result

    # ── Win condition ─────────────────────────────────────────────

    def check_win_condition(self):
        """Returns 'player_win', 'player_lose', or None."""
        from entities.building import Mothership
        for e in self.entities:
            if isinstance(e, Mothership):
                if e.hp <= 0:
                    return "player_win" if e.team == TEAM_ENEMY else "player_lose"
        return None
