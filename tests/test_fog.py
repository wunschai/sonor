"""Tests for FogMap — three-state fog of war."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from core.fog import FogMap
from entities.unit import Unit
from constants import TEAM_PLAYER, TEAM_ENEMY, MAP_WIDTH, MAP_HEIGHT


def _unit(pos, vision_radius=120.0, team=TEAM_PLAYER):
    return Unit(pos=pos, hp=100, size="S", team=team,
                vision_radius=vision_radius, speed=80.0)


class TestFogMapStates:
    def test_initial_state_all_dark(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        assert fog.get_state(0, 0)   == FogMap.DARK
        assert fog.get_state(500, 500) == FogMap.DARK
        assert fog.get_state(MAP_WIDTH - 1, MAP_HEIGHT - 1) == FogMap.DARK

    def test_update_marks_visible_around_unit(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        u = _unit((500, 500), vision_radius=100.0)
        fog.update([u])
        # Centre should be VISIBLE
        assert fog.get_state(500, 500) == FogMap.VISIBLE

    def test_update_visible_within_radius(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        r = 80
        u = _unit((400, 400), vision_radius=r)
        fog.update([u])
        # A point just inside
        assert fog.get_state(440, 400) == FogMap.VISIBLE

    def test_update_dark_outside_radius(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        r = 50
        u = _unit((200, 200), vision_radius=r)
        fog.update([u])
        # A point well outside
        assert fog.get_state(400, 400) == FogMap.DARK

    def test_unit_moves_away_leaves_shroud(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        u = _unit((300, 300), vision_radius=80.0)
        fog.update([u])
        assert fog.get_state(300, 300) == FogMap.VISIBLE
        # Move unit far away
        u.pos = pygame.Vector2(2000, 2000)
        fog.update([u])
        # Previous location should now be SHROUD (was seen)
        assert fog.get_state(300, 300) == FogMap.SHROUD

    def test_dark_area_stays_dark_after_update(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        u = _unit((100, 100), vision_radius=50.0)
        fog.update([u])
        # Far corner never seen
        assert fog.get_state(2900, 2900) == FogMap.DARK

    def test_shroud_not_overwritten_to_dark(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        u = _unit((500, 500), vision_radius=100.0)
        fog.update([u])           # marks (500,500) as VISIBLE
        u.pos = pygame.Vector2(2000, 2000)
        fog.update([u])           # (500,500) should be SHROUD, not DARK
        assert fog.get_state(500, 500) == FogMap.SHROUD


class TestFogMapIsVisible:
    def test_visible_point(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        u = _unit((600, 600), vision_radius=100.0)
        fog.update([u])
        assert fog.is_visible((600, 600)) is True

    def test_dark_point_not_visible(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        fog.update([])
        assert fog.is_visible((600, 600)) is False

    def test_shroud_point_not_visible(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        u = _unit((600, 600), vision_radius=100.0)
        fog.update([u])
        u.pos = pygame.Vector2(2000, 2000)
        fog.update([u])
        assert fog.is_visible((600, 600)) is False


class TestFogMapMultipleUnits:
    def test_multiple_units_union_visible(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        u1 = _unit((200, 200), vision_radius=80.0)
        u2 = _unit((800, 800), vision_radius=80.0)
        fog.update([u1, u2])
        assert fog.get_state(200, 200) == FogMap.VISIBLE
        assert fog.get_state(800, 800) == FogMap.VISIBLE
        assert fog.get_state(500, 500) == FogMap.DARK

    def test_only_player_units_used(self):
        """Enemy units should NOT reveal fog."""
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        enemy = _unit((500, 500), vision_radius=200.0, team=TEAM_ENEMY)
        fog.update([enemy])
        assert fog.get_state(500, 500) == FogMap.DARK


class TestFogMapRevealedPositions:
    def test_asteroid_reveal_persists(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        fog.add_revealed_position((1000, 1000))
        # Even with no units visible there, position is in revealed set
        assert (1000, 1000) in fog.revealed_positions

    def test_revealed_positions_start_empty(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        assert len(fog.revealed_positions) == 0
