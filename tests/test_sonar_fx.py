"""Tests for ui/sonar_fx.py — SonarFX pulse ring and hit flash."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from core.sonar import ActivePulse, SonarHit
from ui.sonar_fx import SonarFX
from constants import PULSE_SPEED, SONAR_HIT_FADE


class TestSonarFXPulse:
    def _surface(self):
        return pygame.Surface((800, 600), pygame.SRCALPHA)

    def test_add_pulse_stored(self):
        fx = SonarFX()
        p = ActivePulse(origin=(100, 100), strength=2)
        fx.add_pulse(p)
        assert len(fx.pulses) == 1

    def test_multiple_pulses_coexist(self):
        fx = SonarFX()
        fx.add_pulse(ActivePulse(origin=(0, 0), strength=1))
        fx.add_pulse(ActivePulse(origin=(200, 200), strength=2))
        assert len(fx.pulses) == 2

    def test_update_advances_pulse_radius(self):
        fx = SonarFX()
        p = ActivePulse(origin=(0, 0), strength=2)
        fx.add_pulse(p)
        fx.update(1.0)
        assert p.radius == pytest.approx(PULSE_SPEED * 1.0)

    def test_dead_pulse_removed_after_update(self):
        """A strength-1 pulse dies after PULSE_DECAY_DIST px; update removes it."""
        from constants import PULSE_DECAY_DIST
        fx = SonarFX()
        p = ActivePulse(origin=(0, 0), strength=1)
        fx.add_pulse(p)
        dt = PULSE_DECAY_DIST / PULSE_SPEED + 0.05
        fx.update(dt)
        assert len(fx.pulses) == 0

    def test_draw_does_not_raise(self):
        fx = SonarFX()
        fx.add_pulse(ActivePulse(origin=(400, 300), strength=2))
        surf = self._surface()
        fx.draw(surf, camera_offset=(0, 0))   # no exception expected

    def test_draw_with_camera_offset_does_not_raise(self):
        fx = SonarFX()
        fx.add_pulse(ActivePulse(origin=(400, 300), strength=2))
        surf = self._surface()
        fx.draw(surf, camera_offset=(100, 50))


class TestSonarFXHit:
    def _hit(self, pos=(100, 100), intensity=2, source="active"):
        return SonarHit(world_pos=pos, intensity=intensity, source=source)

    def _surface(self):
        return pygame.Surface((800, 600), pygame.SRCALPHA)

    def test_add_hit_stored(self):
        fx = SonarFX()
        fx.add_hit(self._hit())
        assert len(fx.hits) == 1

    def test_hit_fade_timer_starts_at_zero(self):
        fx = SonarFX()
        h = self._hit()
        fx.add_hit(h)
        assert h.fade_timer == pytest.approx(0.0)

    def test_hit_fade_timer_advances_with_update(self):
        fx = SonarFX()
        h = self._hit()
        fx.add_hit(h)
        fx.update(0.5)
        assert h.fade_timer == pytest.approx(0.5)

    def test_expired_hit_removed(self):
        fx = SonarFX()
        fx.add_hit(self._hit())
        fx.update(SONAR_HIT_FADE + 0.1)
        assert len(fx.hits) == 0

    def test_hit_intensity_maps_to_line_width(self):
        """SonarFX must expose a method/attribute that maps intensity→line width."""
        fx = SonarFX()
        assert fx.intensity_line_width(1) == 1
        assert fx.intensity_line_width(2) == 2
        assert fx.intensity_line_width(3) == 3

    def test_passive_hit_stored_separately_or_same(self):
        """Passive hits (source='passive') should also be stored in fx.hits."""
        fx = SonarFX()
        fx.add_hit(self._hit(source="passive"))
        assert len(fx.hits) == 1

    def test_draw_hit_does_not_raise(self):
        fx = SonarFX()
        fx.add_hit(self._hit(pos=(200, 150), intensity=2))
        surf = self._surface()
        fx.draw(surf, camera_offset=(0, 0))

    def test_draw_with_offset_does_not_raise(self):
        fx = SonarFX()
        fx.add_hit(self._hit(pos=(500, 400), intensity=3))
        surf = self._surface()
        fx.draw(surf, camera_offset=(200, 100))
