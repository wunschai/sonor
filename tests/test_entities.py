"""Tests for Unit, Ship, Building, Asteroid entities."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from entities.unit import Unit
from entities.ship import CombatShip, MiningShip, BuilderShip
from entities.building import Mothership, MiningStation, Turret
from entities.asteroid import Asteroid
from constants import (
    TEAM_PLAYER, TEAM_ENEMY,
    SHIP_HP, SHIP_SPEED, SHIP_VISION, SHIP_SONAR_STR,
    MOTHERSHIP_HP, MOTHERSHIP_VISION,
    MINING_SHIP_HP, MINING_SHIP_SPEED, MINING_SHIP_VISION,
    BUILDER_SHIP_HP, BUILDER_SHIP_SPEED,
    TURRET_HP, TURRET_DAMAGE, TURRET_FIRE_RATE, TURRET_ATTACK_RANGE,
    STATION_HP, STATION_MINE_RATE, STATION_BUFFER_CAP,
    CARGO_CAP, BOOST_SPEED_MULT,
)


# ─── Unit base class ─────────────────────────────────────────────

class TestUnit:
    def _make(self, **kw):
        defaults = dict(pos=(100.0, 200.0), hp=100, size="S",
                        team=TEAM_PLAYER, vision_radius=120.0, speed=80.0)
        defaults.update(kw)
        return Unit(**defaults)

    def test_pos_stored_as_vector2(self):
        u = self._make(pos=(10.0, 20.0))
        assert u.pos.x == pytest.approx(10.0)
        assert u.pos.y == pytest.approx(20.0)

    def test_hp_and_max_hp(self):
        u = self._make(hp=150)
        assert u.hp == 150
        assert u.max_hp == 150

    def test_size(self):
        u = self._make(size="M")
        assert u.size == "M"

    def test_team(self):
        u = self._make(team=TEAM_ENEMY)
        assert u.team == TEAM_ENEMY

    def test_vision_radius(self):
        u = self._make(vision_radius=200.0)
        assert u.vision_radius == pytest.approx(200.0)

    def test_speed(self):
        u = self._make(speed=120.0)
        assert u.speed == pytest.approx(120.0)

    def test_take_damage_reduces_hp(self):
        u = self._make(hp=100)
        dead = u.take_damage(30)
        assert u.hp == 70
        assert dead is False

    def test_take_damage_returns_true_when_dead(self):
        u = self._make(hp=50)
        dead = u.take_damage(50)
        assert u.hp == 0
        assert dead is True

    def test_take_damage_overkill_clamps_to_zero(self):
        u = self._make(hp=10)
        dead = u.take_damage(999)
        assert u.hp == 0
        assert dead is True

    def test_alive_flag(self):
        u = self._make(hp=100)
        assert u.alive is True
        u.take_damage(100)
        assert u.alive is False


# ─── CombatShip ──────────────────────────────────────────────────

class TestCombatShip:
    def test_small_ship_stats(self):
        s = CombatShip(pos=(0, 0), size="S", team=TEAM_PLAYER)
        assert s.hp      == SHIP_HP["S"]
        assert s.speed   == pytest.approx(SHIP_SPEED["S"])
        assert s.vision_radius == pytest.approx(SHIP_VISION["S"])

    def test_medium_ship_stats(self):
        s = CombatShip(pos=(0, 0), size="M", team=TEAM_PLAYER)
        assert s.hp    == SHIP_HP["M"]
        assert s.speed == pytest.approx(SHIP_SPEED["M"])

    def test_large_ship_stats(self):
        s = CombatShip(pos=(0, 0), size="L", team=TEAM_PLAYER)
        assert s.hp    == SHIP_HP["L"]
        assert s.speed == pytest.approx(SHIP_SPEED["L"])

    def test_sonar_controller_defaults_off(self):
        s = CombatShip(pos=(0, 0), size="S", team=TEAM_PLAYER)
        assert s.sonar.active is False

    def test_sonar_strength_matches_size(self):
        for sz in ("S", "M", "L"):
            s = CombatShip(pos=(0, 0), size=sz, team=TEAM_PLAYER)
            assert s.sonar_strength == SHIP_SONAR_STR[sz]

    def test_speed_mode_defaults_normal(self):
        s = CombatShip(pos=(0, 0), size="S", team=TEAM_PLAYER)
        assert s.speed_mode.boosting is False

    def test_effective_speed_normal(self):
        s = CombatShip(pos=(0, 0), size="S", team=TEAM_PLAYER)
        assert s.speed_mode.effective_speed(s.speed) == pytest.approx(s.speed)

    def test_effective_speed_boost(self):
        s = CombatShip(pos=(0, 0), size="S", team=TEAM_PLAYER)
        s.speed_mode.toggle()
        assert s.speed_mode.effective_speed(s.speed) == pytest.approx(s.speed * BOOST_SPEED_MULT)


# ─── MiningShip ──────────────────────────────────────────────────

class TestMiningShip:
    def test_stats(self):
        m = MiningShip(pos=(0, 0), team=TEAM_PLAYER)
        assert m.hp    == MINING_SHIP_HP
        assert m.speed == pytest.approx(MINING_SHIP_SPEED)
        assert m.vision_radius == pytest.approx(MINING_SHIP_VISION)

    def test_initial_cargo_zero(self):
        m = MiningShip(pos=(0, 0), team=TEAM_PLAYER)
        assert m.cargo == 0

    def test_cargo_cap(self):
        m = MiningShip(pos=(0, 0), team=TEAM_PLAYER)
        assert m.cargo_cap == CARGO_CAP

    def test_initial_state_idle(self):
        m = MiningShip(pos=(0, 0), team=TEAM_PLAYER)
        assert m.state == "IDLE"

    def test_assigned_asteroid_none(self):
        m = MiningShip(pos=(0, 0), team=TEAM_PLAYER)
        assert m.assigned_asteroid is None

    def test_has_sonar(self):
        m = MiningShip(pos=(0, 0), team=TEAM_PLAYER)
        assert hasattr(m, "sonar")
        assert m.sonar.active is False

    def test_has_speed_mode(self):
        m = MiningShip(pos=(0, 0), team=TEAM_PLAYER)
        assert hasattr(m, "speed_mode")


# ─── BuilderShip ─────────────────────────────────────────────────

class TestBuilderShip:
    def test_stats(self):
        b = BuilderShip(pos=(0, 0), team=TEAM_PLAYER)
        assert b.hp    == BUILDER_SHIP_HP
        assert b.speed == pytest.approx(BUILDER_SHIP_SPEED)

    def test_initial_state(self):
        b = BuilderShip(pos=(0, 0), team=TEAM_PLAYER)
        assert b.state == "IDLE"
        assert b.assigned_target is None
        assert b.building_type is None

    def test_has_sonar_and_speed_mode(self):
        b = BuilderShip(pos=(0, 0), team=TEAM_PLAYER)
        assert hasattr(b, "sonar")
        assert hasattr(b, "speed_mode")


# ─── Buildings ───────────────────────────────────────────────────

class TestMothership:
    def test_hp(self):
        m = Mothership(pos=(1500, 1500), team=TEAM_PLAYER)
        assert m.hp    == MOTHERSHIP_HP
        assert m.max_hp == MOTHERSHIP_HP

    def test_vision(self):
        m = Mothership(pos=(1500, 1500), team=TEAM_PLAYER)
        assert m.vision_radius == pytest.approx(MOTHERSHIP_VISION)

    def test_speed_zero(self):
        m = Mothership(pos=(1500, 1500), team=TEAM_PLAYER)
        assert m.speed == pytest.approx(0.0)

    def test_has_two_build_queues(self):
        m = Mothership(pos=(1500, 1500), team=TEAM_PLAYER)
        assert len(m.build_queues) == 2


class TestMiningStation:
    def test_hp(self):
        s = MiningStation(pos=(500, 500), team=TEAM_PLAYER)
        assert s.hp == STATION_HP

    def test_buffer_starts_empty(self):
        s = MiningStation(pos=(500, 500), team=TEAM_PLAYER)
        assert s.buffer == 0

    def test_buffer_cap(self):
        s = MiningStation(pos=(500, 500), team=TEAM_PLAYER)
        assert s.buffer_cap == STATION_BUFFER_CAP

    def test_mine_rate(self):
        s = MiningStation(pos=(500, 500), team=TEAM_PLAYER)
        assert s.mine_rate == pytest.approx(STATION_MINE_RATE)

    def test_attached_asteroid_none(self):
        s = MiningStation(pos=(500, 500), team=TEAM_PLAYER)
        assert s.attached_asteroid is None


class TestTurret:
    def test_stats(self):
        t = Turret(pos=(800, 800), team=TEAM_PLAYER)
        assert t.hp           == TURRET_HP
        assert t.damage       == TURRET_DAMAGE
        assert t.fire_rate    == pytest.approx(TURRET_FIRE_RATE)
        assert t.attack_range == pytest.approx(TURRET_ATTACK_RANGE)

    def test_speed_zero(self):
        t = Turret(pos=(800, 800), team=TEAM_PLAYER)
        assert t.speed == pytest.approx(0.0)


# ─── Asteroid ────────────────────────────────────────────────────

class TestAsteroid:
    def test_sizes(self):
        for sz in ("S", "M", "L"):
            a = Asteroid(pos=(100, 100), size=sz)
            assert a.size == sz

    def test_revealed_defaults_false(self):
        a = Asteroid(pos=(100, 100), size="M")
        assert a.revealed is False

    def test_can_set_revealed(self):
        a = Asteroid(pos=(100, 100), size="M")
        a.revealed = True
        assert a.revealed is True

    def test_ore_infinite(self):
        import math
        a = Asteroid(pos=(100, 100), size="L")
        assert math.isinf(a.ore_amount)
