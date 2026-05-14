"""Tests for World spatial container."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from core.world import World
from entities.unit import Unit
from entities.asteroid import Asteroid
from constants import TEAM_PLAYER, TEAM_ENEMY, MAP_WIDTH, MAP_HEIGHT


def _unit(pos, team=TEAM_PLAYER):
    return Unit(pos=pos, hp=100, size="S", team=team,
                vision_radius=120.0, speed=80.0)


class TestWorld:
    def test_map_size(self):
        w = World()
        assert w.width  == MAP_WIDTH
        assert w.height == MAP_HEIGHT

    def test_add_entity(self):
        w = World()
        u = _unit((100, 100))
        w.add_entity(u)
        assert u in w.entities

    def test_remove_entity(self):
        w = World()
        u = _unit((100, 100))
        w.add_entity(u)
        w.remove_entity(u)
        assert u not in w.entities

    def test_entities_by_team(self):
        w = World()
        p = _unit((100, 100), team=TEAM_PLAYER)
        e = _unit((200, 200), team=TEAM_ENEMY)
        w.add_entity(p)
        w.add_entity(e)
        assert p in w.entities_for_team(TEAM_PLAYER)
        assert e not in w.entities_for_team(TEAM_PLAYER)

    def test_entities_in_radius(self):
        w = World()
        near = _unit((100, 100))
        far  = _unit((900, 900))
        w.add_entity(near)
        w.add_entity(far)
        results = w.entities_in_radius((100, 100), 50)
        assert near in results
        assert far  not in results

    def test_entities_in_radius_boundary(self):
        w = World()
        u = _unit((150, 100))
        w.add_entity(u)
        # exact boundary: distance = 50, radius = 50
        results = w.entities_in_radius((100, 100), 50)
        assert u in results

    def test_add_asteroid(self):
        w = World()
        a = Asteroid(pos=(500, 500), size="M")
        w.add_entity(a)
        assert a in w.asteroids

    def test_resources_start_zero(self):
        w = World()
        assert w.resources[TEAM_PLAYER] == 0
        assert w.resources[TEAM_ENEMY]  == 0

    def test_add_resources(self):
        w = World()
        w.resources[TEAM_PLAYER] += 100
        assert w.resources[TEAM_PLAYER] == 100
