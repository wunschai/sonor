"""Minimap — renders a scaled-down overview of the world with sonar contacts."""
from __future__ import annotations
import pygame

from core.sonar import SonarHit
from constants import TEAM_PLAYER, SONAR_HIT_FADE


# Dot colours
_COL_PLAYER   = (80,  200, 255)   # player units — light blue
_COL_ENEMY    = (255, 60,  60)    # enemy units  — red
_COL_ASTEROID = (80,  200, 80)    # revealed asteroids — green
_COL_HIT_ACT  = (255, 255, 255)   # active sonar hit  — white
_COL_HIT_PAS  = (255, 160, 40)    # passive sonar hit — orange

# Active/passive hit radii per intensity level
_HIT_RADII = {1: 4, 2: 8, 3: 14}


class Minimap:
    """Draws a minimap corner panel and sonar contacts."""

    def __init__(
        self,
        *,
        map_w: int,
        map_h: int,
        mm_w: int = 200,
        mm_h: int = 200,
    ):
        self.map_w = map_w
        self.map_h = map_h
        self.mm_w  = mm_w
        self.mm_h  = mm_h

    # ── Coordinate mapping ────────────────────────────────────────

    def world_to_minimap(self, wx: float, wy: float) -> tuple[float, float]:
        sx = wx / self.map_w * self.mm_w
        sy = wy / self.map_h * self.mm_h
        return sx, sy

    # ── Hit radius helper ─────────────────────────────────────────

    def hit_radius(self, source: str, intensity: int) -> int:
        """Return the dot radius in minimap pixels for a sonar hit."""
        return _HIT_RADII.get(intensity, 4)

    # ── Main draw ─────────────────────────────────────────────────

    def draw(
        self,
        surface: pygame.Surface,
        world,
        sonar_hits: list[SonarHit],
    ) -> None:
        """Render the minimap onto *surface* starting at top-left (0, 0)."""
        # Background
        pygame.draw.rect(surface, (10, 10, 20), (0, 0, self.mm_w, self.mm_h))
        pygame.draw.rect(surface, (40, 40, 60), (0, 0, self.mm_w, self.mm_h), 1)

        # Entity dots
        for entity in world.entities:
            from entities.asteroid import Asteroid
            if isinstance(entity, Asteroid):
                if not getattr(entity, "revealed", False):
                    continue
                sx, sy = self.world_to_minimap(entity.pos.x, entity.pos.y)
                pygame.draw.rect(surface, _COL_ASTEROID,
                                 (int(sx) - 2, int(sy) - 2, 4, 4))
                continue

            team = getattr(entity, "team", None)
            col  = _COL_PLAYER if team == TEAM_PLAYER else _COL_ENEMY
            sx, sy = self.world_to_minimap(entity.pos.x, entity.pos.y)
            pygame.draw.circle(surface, col, (int(sx), int(sy)), 2)

        # Sonar hit dots
        for hit in sonar_hits:
            if hit.fade_timer >= SONAR_HIT_FADE:
                continue
            progress = hit.fade_timer / SONAR_HIT_FADE
            alpha    = max(0, int(255 * (1.0 - progress)))
            col      = _COL_HIT_ACT if hit.source == "active" else _COL_HIT_PAS
            r        = self.hit_radius(hit.source, hit.intensity)
            wx, wy   = hit.world_pos
            sx, sy   = self.world_to_minimap(wx, wy)

            # Draw with alpha on a temp surface
            tmp = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (*col, alpha), (r + 1, r + 1), r)
            surface.blit(tmp, (int(sx) - r - 1, int(sy) - r - 1))
