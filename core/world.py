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
        player_ms = [e for e in self.entities
                     if isinstance(e, Mothership) and e.team == TEAM_PLAYER]
        enemy_ms  = [e for e in self.entities
                     if isinstance(e, Mothership) and e.team == TEAM_ENEMY]

        # Dead mothership still in world
        for e in player_ms:
            if e.hp <= 0:
                return "player_lose"
        for e in enemy_ms:
            if e.hp <= 0:
                return "player_win"

        # Mothership removed from world entirely
        if player_ms and not enemy_ms:
            return "player_win"
        if enemy_ms and not player_ms:
            return "player_lose"

        return None
