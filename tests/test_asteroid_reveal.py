"""Tests for asteroid reveal logic — fog visibility and sonar hit integration."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from core.world import World
from core.fog import FogMap
from core.sonar import SonarHit
from entities.asteroid import Asteroid
from entities.ship import MiningShip
from systems.mining import MiningSystem
from constants import TEAM_PLAYER, MAP_WIDTH, MAP_HEIGHT


def _world():
    return World()


def _asteroid(pos=(500, 500), size="M"):
    return Asteroid(pos=pos, size=size)


class TestAsteroidReveal:
    def test_asteroid_starts_unrevealed(self):
        ast = _asteroid()
        assert ast.revealed is False

    def test_fog_visible_reveals_asteroid(self):
        """When asteroid is in VISIBLE fog, fog.reveal_asteroids marks it revealed."""
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        ast = _asteroid(pos=(500, 500))
        # Manually set the fog cell to VISIBLE
        fog._state[500, 500] = FogMap.VISIBLE
        fog._seen [500, 500] = True
        fog.reveal_asteroids([ast])
        assert ast.revealed is True

    def test_fog_dark_does_not_reveal_asteroid(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        ast = _asteroid(pos=(500, 500))
        # State starts DARK by default
        fog.reveal_asteroids([ast])
        assert ast.revealed is False

    def test_fog_shroud_does_not_reveal_asteroid(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        ast = _asteroid(pos=(500, 500))
        fog._state[500, 500] = FogMap.SHROUD
        fog.reveal_asteroids([ast])
        assert ast.revealed is False

    def test_sonar_hit_reveals_asteroid(self):
        """A SonarHit whose world_pos matches an asteroid reveals it."""
        w = _world()
        ast = _asteroid(pos=(300, 0))
        w.add_entity(ast)
        hit = SonarHit(world_pos=(300, 0), intensity=2, source="active")
        sys = MiningSystem()
        sys.reveal_by_hits(w, [hit])
        assert ast.revealed is True

    def test_sonar_hit_far_from_asteroid_does_not_reveal(self):
        w = _world()
        ast = _asteroid(pos=(300, 0))
        w.add_entity(ast)
        hit = SonarHit(world_pos=(600, 0), intensity=2, source="active")
        sys = MiningSystem()
        sys.reveal_by_hits(w, [hit])
        assert ast.revealed is False

    def test_already_revealed_stays_revealed(self):
        w = _world()
        ast = _asteroid(pos=(300, 0))
        ast.revealed = True
        w.add_entity(ast)
        sys = MiningSystem()
        sys.reveal_by_hits(w, [])
        assert ast.revealed is True

    def test_reveal_adds_to_fog_revealed_positions(self):
        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        ast = _asteroid(pos=(500, 500))
        fog._state[500, 500] = FogMap.VISIBLE
        fog._seen [500, 500] = True
        fog.reveal_asteroids([ast])
        assert (500, 500) in fog.revealed_positions
