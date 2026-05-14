"""FogMap — three-state fog of war backed by a numpy array.

States
------
DARK    (0) — never seen, fully opaque black
SHROUD  (1) — previously seen, semi-transparent overlay
VISIBLE (2) — currently within a player unit's vision radius
"""
import numpy as np
import pygame
from constants import TEAM_PLAYER, COL_SHROUD


class FogMap:
    DARK    = 0
    SHROUD  = 1
    VISIBLE = 2

    def __init__(self, width: int, height: int):
        self.width  = width
        self.height = height
        # _state[y, x] — starts DARK everywhere
        self._state = np.zeros((height, width), dtype=np.uint8)
        # _seen[y, x] — True once any player unit has seen the cell
        self._seen  = np.zeros((height, width), dtype=bool)
        self.revealed_positions: set = set()   # asteroid / landmark markers

    # ── State access ──────────────────────────────────────────────

    def get_state(self, x: int, y: int) -> int:
        x = max(0, min(x, self.width  - 1))
        y = max(0, min(y, self.height - 1))
        return int(self._state[y, x])

    def is_visible(self, pos) -> bool:
        x, y = int(pos[0]), int(pos[1])
        return self.get_state(x, y) == self.VISIBLE

    # ── Update ────────────────────────────────────────────────────

    def update(self, player_units: list):
        """Recompute fog every frame based on current player unit positions."""
        # 1. Reset to SHROUD where previously seen, else keep DARK
        self._state[:] = np.where(self._seen, self.SHROUD, self.DARK)

        # 2. Paint VISIBLE circles around each player unit
        for unit in player_units:
            if getattr(unit, "team", None) != TEAM_PLAYER:
                continue
            cx = int(unit.pos.x)
            cy = int(unit.pos.y)
            r  = int(unit.vision_radius)

            # Bounding box clamped to map
            x0 = max(0, cx - r)
            x1 = min(self.width,  cx + r + 1)
            y0 = max(0, cy - r)
            y1 = min(self.height, cy + r + 1)

            xs = np.arange(x0, x1)
            ys = np.arange(y0, y1)
            gx, gy = np.meshgrid(xs, ys)
            mask = (gx - cx) ** 2 + (gy - cy) ** 2 <= r * r
            self._state[y0:y1, x0:x1][mask] = self.VISIBLE
            self._seen [y0:y1, x0:x1][mask] = True

    # ── Persistent markers ────────────────────────────────────────

    def add_revealed_position(self, pos):
        """Mark a world position as permanently revealed (e.g. discovered asteroid)."""
        self.revealed_positions.add((int(pos[0]), int(pos[1])))

    def reveal_asteroids(self, asteroids: list):
        """Check each asteroid — if currently VISIBLE, mark it as revealed."""
        for asteroid in asteroids:
            if self.is_visible(asteroid.pos):
                asteroid.revealed = True
                self.add_revealed_position(asteroid.pos)

    # ── Rendering ─────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera_offset: tuple):
        """Overlay fog onto the given surface (should cover the full screen)."""
        cam_x, cam_y = int(camera_offset[0]), int(camera_offset[1])
        sw = surface.get_width()
        sh = surface.get_height()

        wx0 = max(0, cam_x)
        wy0 = max(0, cam_y)
        wx1 = min(self.width,  cam_x + sw)
        wy1 = min(self.height, cam_y + sh)

        sx0 = wx0 - cam_x
        sy0 = wy0 - cam_y

        region = self._state[wy0:wy1, wx0:wx1]   # shape: (h, w)
        h, w = region.shape

        if w <= 0 or h <= 0:
            return

        fog_surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # Build alpha channel: DARK=255, SHROUD=160, VISIBLE=0
        alpha = np.zeros((h, w), dtype=np.uint8)
        alpha[region == self.DARK]   = 255
        alpha[region == self.SHROUD] = 160

        # surfarray uses (x, y) indexing, region is (y, x) → transpose
        pygame.surfarray.pixels_alpha(fog_surf)[:] = alpha.T
        del alpha   # release lock

        surface.blit(fog_surf, (sx0, sy0))
