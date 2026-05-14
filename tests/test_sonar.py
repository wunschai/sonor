"""Tests for SonarController, SpeedMode, ActivePulse, PassiveDetector."""
import pytest, sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from entities.ship import SonarController, SpeedMode, CombatShip, MiningShip
from entities.unit import Unit
from core.sonar import ActivePulse, SonarHit, PassiveDetector
from constants import (
    TEAM_PLAYER, TEAM_ENEMY,
    SONAR_INTERVAL, PULSE_SPEED, PULSE_DECAY_DIST, SONAR_HIT_FADE,
    PASSIVE_RADIUS, PASSIVE_NOISE, PASSIVE_FADE,
    PASSIVE_VOL_L1, PASSIVE_VOL_L2, SIZE_FACTORS, BOOST_SPEED_MULT,
)


# ─── SonarController ─────────────────────────────────────────────

class TestSonarController:
    def test_defaults_inactive(self):
        sc = SonarController()
        assert sc.active is False

    def test_toggle_activates(self):
        sc = SonarController()
        sc.toggle()
        assert sc.active is True

    def test_toggle_deactivates(self):
        sc = SonarController()
        sc.toggle()
        sc.toggle()
        assert sc.active is False

    def test_toggle_off_resets_timer(self):
        sc = SonarController()
        sc.toggle()
        sc.update(1.5)   # advance timer
        sc.toggle()      # turn off
        assert sc.timer == pytest.approx(0.0)

    def test_update_returns_false_when_inactive(self):
        sc = SonarController()
        assert sc.update(10.0) is False

    def test_update_returns_false_before_interval(self):
        sc = SonarController(interval=3.0)
        sc.toggle()
        assert sc.update(2.9) is False

    def test_update_returns_true_at_interval(self):
        sc = SonarController(interval=3.0)
        sc.toggle()
        assert sc.update(3.0) is True

    def test_update_resets_timer_after_fire(self):
        sc = SonarController(interval=3.0)
        sc.toggle()
        sc.update(3.0)
        # Timer should have wrapped — next fire in another 3s
        assert sc.update(2.9) is False
        assert sc.update(0.2) is True   # 2.9 + 0.2 = 3.1 > 3.0

    def test_update_accumulates_across_calls(self):
        sc = SonarController(interval=3.0)
        sc.toggle()
        sc.update(1.0)
        sc.update(1.0)
        assert sc.update(1.0) is True


# ─── SpeedMode ───────────────────────────────────────────────────

class TestSpeedMode:
    def test_defaults_not_boosting(self):
        sm = SpeedMode()
        assert sm.boosting is False

    def test_toggle_sets_boosting(self):
        sm = SpeedMode()
        sm.toggle()
        assert sm.boosting is True

    def test_effective_speed_normal(self):
        sm = SpeedMode()
        assert sm.effective_speed(100.0) == pytest.approx(100.0)

    def test_effective_speed_boost(self):
        sm = SpeedMode()
        sm.toggle()
        assert sm.effective_speed(100.0) == pytest.approx(100.0 * BOOST_SPEED_MULT)

    def test_volume_uses_effective_speed(self):
        """Volume for passive sonar should use effective (boosted) speed."""
        sm = SpeedMode()
        sm.toggle()
        base = 50.0
        effective = sm.effective_speed(base)
        assert effective == pytest.approx(base * BOOST_SPEED_MULT)


# ─── ActivePulse ─────────────────────────────────────────────────

class TestActivePulse:
    def _make(self, origin=(0, 0), strength=2):
        return ActivePulse(origin=origin, strength=strength)

    def test_initial_radius_zero(self):
        p = self._make()
        assert p.radius == pytest.approx(0.0)

    def test_initial_strength(self):
        p = self._make(strength=3)
        assert p.strength == 3

    def test_radius_grows_with_dt(self):
        p = self._make()
        p.update(1.0)
        assert p.radius == pytest.approx(PULSE_SPEED * 1.0)

    def test_strength_decays_after_decay_dist(self):
        p = self._make(strength=2)
        # Advance until radius crosses PULSE_DECAY_DIST
        dt = PULSE_DECAY_DIST / PULSE_SPEED + 0.01
        alive = p.update(dt)
        assert p.strength == 1
        assert alive is True

    def test_pulse_dies_when_strength_zero(self):
        p = self._make(strength=1)
        dt = PULSE_DECAY_DIST / PULSE_SPEED + 0.01
        alive = p.update(dt)
        assert alive is False

    def test_strength_3_decays_twice_survives(self):
        p = self._make(strength=3)
        dt = PULSE_DECAY_DIST / PULSE_SPEED + 0.01
        p.update(dt)   # → strength 2
        alive = p.update(dt)   # → strength 1
        assert alive is True
        assert p.strength == 1

    def test_check_hit_detects_entity_on_ring(self):
        p = self._make(origin=(0, 0), strength=2)
        # Place an entity at exactly radius distance from origin
        target_dist = 150.0
        p.update(target_dist / PULSE_SPEED)   # radius ≈ 150
        entity = Unit(pos=(target_dist, 0), hp=100, size="M",
                      team=TEAM_ENEMY, vision_radius=100, speed=0)
        hits = p.check_hit([entity])
        assert len(hits) == 1
        assert hits[0].intensity == min(2, 2)   # entity M=2, pulse strength=2

    def test_check_hit_misses_entity_far_away(self):
        p = self._make(origin=(0, 0), strength=2)
        p.update(0.5)   # radius = 100
        entity = Unit(pos=(500, 0), hp=100, size="S",
                      team=TEAM_ENEMY, vision_radius=100, speed=0)
        hits = p.check_hit([entity])
        assert len(hits) == 0

    def test_check_hit_intensity_capped_by_pulse_strength(self):
        p = self._make(origin=(0, 0), strength=1)   # weak pulse
        target_dist = 150.0
        p.update(target_dist / PULSE_SPEED)
        entity = Unit(pos=(target_dist, 0), hp=100, size="L",
                      team=TEAM_ENEMY, vision_radius=100, speed=0)
        hits = p.check_hit([entity])
        assert len(hits) == 1
        assert hits[0].intensity == 1   # capped by pulse strength

    def test_check_hit_multiple_entities(self):
        p = self._make(origin=(0, 0), strength=2)
        r = 200.0
        p.update(r / PULSE_SPEED)
        e1 = Unit(pos=(r, 0), hp=100, size="S", team=TEAM_ENEMY,
                  vision_radius=100, speed=0)
        e2 = Unit(pos=(0, r), hp=100, size="S", team=TEAM_ENEMY,
                  vision_radius=100, speed=0)
        hits = p.check_hit([e1, e2])
        assert len(hits) == 2

    def test_sonar_hit_source_is_active(self):
        p = self._make(origin=(0, 0), strength=1)
        target_dist = 100.0
        p.update(target_dist / PULSE_SPEED)
        entity = Unit(pos=(target_dist, 0), hp=100, size="S",
                      team=TEAM_ENEMY, vision_radius=100, speed=0)
        hits = p.check_hit([entity])
        assert hits[0].source == "active"


# ─── PassiveDetector ─────────────────────────────────────────────

class TestPassiveDetector:
    def _enemy(self, pos, size="M", speed=0.0):
        u = Unit(pos=pos, hp=100, size=size, team=TEAM_ENEMY,
                 vision_radius=100, speed=speed)
        u._current_speed = speed   # track actual movement speed
        return u

    def _detector_unit(self, pos):
        return Unit(pos=pos, hp=100, size="S", team=TEAM_PLAYER,
                    vision_radius=120, speed=0)

    def test_stationary_enemy_not_detected(self):
        detector = PassiveDetector()
        viewer = self._detector_unit((0, 0))
        enemy = self._enemy((100, 0), speed=0.0)
        hits = detector.detect([viewer], [enemy])
        assert len(hits) == 0

    def test_moving_enemy_within_radius_detected(self):
        detector = PassiveDetector()
        viewer = self._detector_unit((0, 0))
        enemy = self._enemy((100, 0), size="M", speed=80.0)
        hits = detector.detect([viewer], [enemy])
        assert len(hits) == 1

    def test_moving_enemy_outside_radius_not_detected(self):
        detector = PassiveDetector()
        viewer = self._detector_unit((0, 0))
        enemy = self._enemy((PASSIVE_RADIUS + 50, 0), size="L", speed=100.0)
        hits = detector.detect([viewer], [enemy])
        assert len(hits) == 0

    def test_intensity_level_1_low_volume(self):
        """volume < PASSIVE_VOL_L1 → intensity 1"""
        detector = PassiveDetector()
        viewer = self._detector_unit((0, 0))
        # S ship (factor=1), speed just below threshold
        speed = PASSIVE_VOL_L1 - 1   # volume = speed * 1 = 39
        enemy = self._enemy((50, 0), size="S", speed=float(speed))
        hits = detector.detect([viewer], [enemy])
        assert len(hits) == 1
        assert hits[0].intensity == 1

    def test_intensity_level_2_medium_volume(self):
        """PASSIVE_VOL_L1 ≤ volume < PASSIVE_VOL_L2 → intensity 2"""
        detector = PassiveDetector()
        viewer = self._detector_unit((0, 0))
        speed = PASSIVE_VOL_L1 + 1   # volume = 41
        enemy = self._enemy((50, 0), size="S", speed=float(speed))
        hits = detector.detect([viewer], [enemy])
        assert hits[0].intensity == 2

    def test_intensity_level_3_high_volume(self):
        """volume ≥ PASSIVE_VOL_L2 → intensity 3"""
        detector = PassiveDetector()
        viewer = self._detector_unit((0, 0))
        speed = PASSIVE_VOL_L2 + 10   # volume = 130
        enemy = self._enemy((50, 0), size="S", speed=float(speed))
        hits = detector.detect([viewer], [enemy])
        assert hits[0].intensity == 3

    def test_position_has_noise(self):
        """Detected position should differ from true position by ≤ PASSIVE_NOISE."""
        import random
        random.seed(0)
        detector = PassiveDetector()
        viewer = self._detector_unit((0, 0))
        enemy = self._enemy((100, 0), size="M", speed=80.0)
        hits = detector.detect([viewer], [enemy])
        assert len(hits) == 1
        dx = abs(hits[0].world_pos[0] - 100.0)
        dy = abs(hits[0].world_pos[1] - 0.0)
        assert dx <= PASSIVE_NOISE
        assert dy <= PASSIVE_NOISE

    def test_player_units_ignored(self):
        """Player units should never trigger passive sonar."""
        detector = PassiveDetector()
        viewer = self._detector_unit((0, 0))
        friendly = Unit(pos=(100, 0), hp=100, size="M", team=TEAM_PLAYER,
                        vision_radius=120, speed=80.0)
        friendly._current_speed = 80.0
        hits = detector.detect([viewer], [friendly])
        assert len(hits) == 0

    def test_source_is_passive(self):
        detector = PassiveDetector()
        viewer = self._detector_unit((0, 0))
        enemy = self._enemy((50, 0), size="M", speed=80.0)
        hits = detector.detect([viewer], [enemy])
        assert hits[0].source == "passive"

    def test_size_factor_scales_volume(self):
        """L ship (factor=3) is louder than S ship (factor=1) at same speed."""
        detector = PassiveDetector()
        viewer = self._detector_unit((0, 0))
        speed = 20.0
        s_enemy = self._enemy((50, 0), size="S", speed=speed)
        l_enemy = self._enemy((50, 0), size="L", speed=speed)
        s_hits = detector.detect([viewer], [s_enemy])
        l_hits = detector.detect([viewer], [l_enemy])
        # S: volume=20 → level 1; L: volume=60 → level 2
        assert s_hits[0].intensity < l_hits[0].intensity
