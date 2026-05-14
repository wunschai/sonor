"""SonarFX — visual effects for active pulse rings and sonar hit flashes."""
from __future__ import annotations
import math
import pygame

from core.sonar import ActivePulse, SonarHit
from constants import SONAR_HIT_FADE, PULSE_SPEED


# Pulse ring colour (cyan-white)
_PULSE_COLOUR = (100, 220, 255)
# Hit flash colours per source
_HIT_COLOUR_ACTIVE  = (255, 255, 255)   # bright white for active hits
_HIT_COLOUR_PASSIVE = (255, 160, 40)    # orange for passive hits


class SonarFX:
    """Manages and renders expanding pulse rings and fading hit markers."""

    def __init__(self):
        self.pulses: list[ActivePulse] = []
        self.hits:   list[SonarHit]   = []

    # ── Public interface ──────────────────────────────────────────

    def add_pulse(self, pulse: ActivePulse) -> None:
        self.pulses.append(pulse)

    def add_hit(self, hit: SonarHit) -> None:
        hit.fade_timer = 0.0
        self.hits.append(hit)

    def update(self, dt: float) -> None:
        """Advance all effects; remove expired ones."""
        # Advance pulses, keep alive ones
        alive = []
        for p in self.pulses:
            if p.update(dt):
                alive.append(p)
        self.pulses = alive

        # Advance hit fade timers
        for h in self.hits:
            h.fade_timer += dt
        self.hits = [h for h in self.hits if h.fade_timer < SONAR_HIT_FADE]

    def intensity_line_width(self, intensity: int) -> int:
        """Map sonar intensity (1/2/3) to line width in pixels."""
        return max(1, intensity)

    def draw(self, surface: pygame.Surface, camera_offset: tuple) -> None:
        """Draw all active effects onto *surface* (screen-space)."""
        cam_x, cam_y = camera_offset
        self._draw_pulses(surface, cam_x, cam_y)
        self._draw_hits(surface, cam_x, cam_y)

    # ── Private drawing ───────────────────────────────────────────

    def _draw_pulses(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        for pulse in self.pulses:
            ox, oy = pulse.origin
            sx = int(ox - cam_x)
            sy = int(oy - cam_y)
            r  = int(pulse.radius)
            if r < 1:
                continue
            # Fade alpha based on strength
            alpha = max(30, min(200, 80 * pulse.strength))
            lw    = self.intensity_line_width(pulse.strength)
            # Draw on a temp surface with alpha to avoid overdraw issues
            self._draw_circle_aa(surface, _PULSE_COLOUR, (sx, sy), r, lw, alpha)

    def _draw_hits(self, surface: pygame.Surface, cam_x: float, cam_y: float) -> None:
        for hit in self.hits:
            wx, wy = hit.world_pos
            sx = int(wx - cam_x)
            sy = int(wy - cam_y)
            progress = hit.fade_timer / SONAR_HIT_FADE          # 0→1
            alpha    = max(0, int(255 * (1.0 - progress)))
            lw       = self.intensity_line_width(hit.intensity)
            r        = {1: 6, 2: 10, 3: 16}.get(hit.intensity, 6)
            colour   = _HIT_COLOUR_PASSIVE if hit.source == "passive" else _HIT_COLOUR_ACTIVE
            self._draw_circle_aa(surface, colour, (sx, sy), r, lw, alpha)

    @staticmethod
    def _draw_circle_aa(
        surface: pygame.Surface,
        colour: tuple,
        center: tuple,
        radius: int,
        width: int,
        alpha: int,
    ) -> None:
        """Draw an anti-aliased circle ring using a temp SRCALPHA surface."""
        if radius < 1:
            return
        pad  = width + 2
        size = (radius + pad) * 2
        tmp  = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = radius + pad
        pygame.draw.circle(tmp, (*colour, alpha), (cx, cy), radius, width)
        dest_x = center[0] - cx
        dest_y = center[1] - cy
        surface.blit(tmp, (dest_x, dest_y))
