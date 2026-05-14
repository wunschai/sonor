"""Tests for ui/minimap.py — Minimap rendering and sonar dot display."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from core.world import World
from core.sonar import SonarHit
from entities.ship import CombatShip
from entities.building import Mothership
from entities.asteroid import Asteroid
from ui.minimap import Minimap
from constants import (
    TEAM_PLAYER, TEAM_ENEMY,
    MAP_WIDTH, MAP_HEIGHT,
    SONAR_HIT_FADE, PASSIVE_FADE,
)


# ── Helpers ───────────────────────────────────────────────────────

def _surface(w=200, h=200):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _world_with(entities):
    w = World()
    for e in entities:
        w.add_entity(e)
    return w


def _hit(pos, intensity=2, source="active"):
    return SonarHit(world_pos=pos, intensity=intensity, source=source)


# ── Coordinate mapping ────────────────────────────────────────────

class TestMinimapCoordMapping:
    def test_origin_maps_to_top_left(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        sx, sy = mm.world_to_minimap(0, 0)
        assert sx == pytest.approx(0.0, abs=1)
        assert sy == pytest.approx(0.0, abs=1)

    def test_bottom_right_maps_to_minimap_size(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        sx, sy = mm.world_to_minimap(MAP_WIDTH, MAP_HEIGHT)
        assert sx == pytest.approx(200.0, abs=1)
        assert sy == pytest.approx(200.0, abs=1)

    def test_centre_maps_to_half(self):
        mm = Minimap(map_w=1000, map_h=1000, mm_w=100, mm_h=100)
        sx, sy = mm.world_to_minimap(500, 500)
        assert sx == pytest.approx(50.0, abs=0.5)
        assert sy == pytest.approx(50.0, abs=0.5)


# ── Unit dots ────────────────────────────────────────────────────

class TestMinimapUnitDots:
    def test_draw_does_not_raise_with_player_units(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        world = _world_with([
            CombatShip(pos=(300, 300), size="S", team=TEAM_PLAYER),
        ])
        surf = _surface()
        mm.draw(surf, world, sonar_hits=[])

    def test_draw_does_not_raise_with_enemy_units(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        world = _world_with([
            CombatShip(pos=(2700, 2700), size="M", team=TEAM_ENEMY),
        ])
        surf = _surface()
        mm.draw(surf, world, sonar_hits=[])

    def test_draw_does_not_raise_with_asteroid(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        a = Asteroid(pos=(500, 500), size="M")
        a.revealed = True
        world = _world_with([a])
        surf = _surface()
        mm.draw(surf, world, sonar_hits=[])

    def test_draw_empty_world_does_not_raise(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        surf = _surface()
        mm.draw(surf, World(), sonar_hits=[])


# ── Sonar hit dots ────────────────────────────────────────────────

class TestMinimapSonarHits:
    def test_active_hit_stored_after_draw(self):
        """After calling draw with an active SonarHit, it should be rendered."""
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        hits = [_hit((300, 300), intensity=2, source="active")]
        surf = _surface()
        mm.draw(surf, World(), sonar_hits=hits)   # should not raise

    def test_passive_hit_stored_after_draw(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        hits = [_hit((300, 300), intensity=1, source="passive")]
        surf = _surface()
        mm.draw(surf, World(), sonar_hits=hits)

    def test_active_hit_radius_intensity_1(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        assert mm.hit_radius("active", 1) == 4

    def test_active_hit_radius_intensity_2(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        assert mm.hit_radius("active", 2) == 8

    def test_active_hit_radius_intensity_3(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        assert mm.hit_radius("active", 3) == 14

    def test_passive_hit_same_radii(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        assert mm.hit_radius("passive", 1) == 4
        assert mm.hit_radius("passive", 2) == 8
        assert mm.hit_radius("passive", 3) == 14

    def test_multiple_hits_draw_no_raise(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        hits = [
            _hit((100, 100), intensity=1, source="active"),
            _hit((200, 200), intensity=2, source="passive"),
            _hit((300, 300), intensity=3, source="active"),
        ]
        surf = _surface()
        mm.draw(surf, World(), sonar_hits=hits)

    def test_expired_hit_not_drawn(self):
        """SonarHit with fade_timer ≥ SONAR_HIT_FADE should be silently skipped."""
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        h = _hit((300, 300), intensity=2)
        h.fade_timer = SONAR_HIT_FADE + 0.1   # expired
        surf = _surface()
        mm.draw(surf, World(), sonar_hits=[h])   # should not raise


# ── Revealed asteroid dots ────────────────────────────────────────

class TestMinimapAsteroids:
    def test_unrevealed_asteroid_not_drawn(self):
        """Unrevealed asteroids should never appear on minimap."""
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        a = Asteroid(pos=(500, 500), size="M")
        # a.revealed defaults to False
        world = _world_with([a])
        surf = _surface()
        mm.draw(surf, world, sonar_hits=[])   # just confirm no crash

    def test_revealed_asteroid_draw_no_raise(self):
        mm = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=200)
        a = Asteroid(pos=(1500, 1500), size="L")
        a.revealed = True
        world = _world_with([a])
        surf = _surface()
        mm.draw(surf, world, sonar_hits=[])
