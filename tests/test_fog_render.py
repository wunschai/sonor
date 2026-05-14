"""Tests for fog rendering logic and mineral marker persistence."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from core.fog import FogMap
from core.render_filter import should_draw_entity
from entities.unit import Unit
from entities.asteroid import Asteroid
from constants import TEAM_PLAYER, TEAM_ENEMY, MAP_WIDTH, MAP_HEIGHT


def _unit(pos, vision=120.0, team=TEAM_PLAYER):
    return Unit(pos=pos, hp=100, size="S", team=team,
                vision_radius=vision, speed=80.0)


class TestRenderFilter:
    """should_draw_entity decides whether an entity is visible to the player."""

    def test_player_unit_always_drawn(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        fog.update([])
        u = _unit((500, 500), team=TEAM_PLAYER)
        assert should_draw_entity(u, fog) is True

    def test_enemy_in_visible_area_drawn(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        viewer = _unit((500, 500), vision=200.0)
        fog.update([viewer])
        enemy = _unit((520, 500), team=TEAM_ENEMY)
        assert should_draw_entity(enemy, fog) is True

    def test_enemy_in_dark_area_not_drawn(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        fog.update([])
        enemy = _unit((500, 500), team=TEAM_ENEMY)
        assert should_draw_entity(enemy, fog) is False

    def test_enemy_in_shroud_not_drawn(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        viewer = _unit((500, 500), vision=100.0)
        fog.update([viewer])
        viewer.pos = pygame.Vector2(2000, 2000)
        fog.update([viewer])
        # (500,500) is now SHROUD
        enemy = _unit((500, 500), team=TEAM_ENEMY)
        assert should_draw_entity(enemy, fog) is False

    def test_asteroid_not_revealed_in_dark_not_drawn(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        fog.update([])
        a = Asteroid(pos=(300, 300), size="M")
        a.revealed = False
        assert should_draw_entity(a, fog) is False

    def test_asteroid_revealed_always_drawn(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        fog.update([])
        a = Asteroid(pos=(300, 300), size="M")
        a.revealed = True
        assert should_draw_entity(a, fog) is True

    def test_asteroid_in_visible_area_drawn(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        viewer = _unit((300, 300), vision=100.0)
        fog.update([viewer])
        a = Asteroid(pos=(310, 300), size="S")
        a.revealed = False
        assert should_draw_entity(a, fog) is True


class TestMineralRevealPersistence:
    def test_revealed_position_persists_after_fog_update(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        fog.add_revealed_position((1200, 1200))
        fog.update([])   # No units — but revealed_positions should survive
        assert (1200, 1200) in fog.revealed_positions

    def test_multiple_revealed_positions(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        for p in [(100, 100), (500, 600), (2000, 2000)]:
            fog.add_revealed_position(p)
        assert len(fog.revealed_positions) == 3

    def test_asteroid_visible_when_in_range_sets_revealed(self):
        """Integration: FogMap.reveal_asteroids() marks asteroids inside VISIBLE."""
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        viewer = _unit((500, 500), vision=200.0)
        fog.update([viewer])
        a = Asteroid(pos=(550, 500), size="M")
        fog.reveal_asteroids([a])
        assert a.revealed is True
        assert (550, 500) in fog.revealed_positions

    def test_asteroid_in_dark_not_revealed(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        fog.update([])
        a = Asteroid(pos=(1500, 1500), size="L")
        fog.reveal_asteroids([a])
        assert a.revealed is False
