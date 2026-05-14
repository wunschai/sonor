"""Tests for systems/build.py — BuildQueue and BuildSystem."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from core.world import World
from entities.ship import BuilderShip
from entities.building import Mothership, MiningStation, BuildQueue
from entities.asteroid import Asteroid
from systems.build import BuildSystem
from constants import (
    TEAM_PLAYER,
    MOTHERSHIP_QUEUE_SLOTS,
    STATION_ATTACH_RADIUS,
)


# ── Helpers ───────────────────────────────────────────────────────

def _world():
    w = World()
    w.resources[TEAM_PLAYER] = 10000   # enough for anything
    return w


def _mothership(pos=(0, 0)):
    return Mothership(pos=pos, team=TEAM_PLAYER)


def _builder(pos=(0, 0)):
    return BuilderShip(pos=pos, team=TEAM_PLAYER)


# ── BuildQueue unit tests ─────────────────────────────────────────

class TestBuildQueue:
    def test_enqueue_succeeds_with_enough_resources(self):
        q = BuildQueue()
        result = q.enqueue("CombatShip_S", build_time=10.0, cost=100, resources=500)
        assert result is True

    def test_enqueue_fails_with_insufficient_resources(self):
        q = BuildQueue()
        result = q.enqueue("CombatShip_L", build_time=70.0, cost=400, resources=50)
        assert result is False

    def test_enqueue_fails_when_queue_full(self):
        q = BuildQueue()
        for _ in range(MOTHERSHIP_QUEUE_SLOTS):
            q.enqueue("CombatShip_S", build_time=10.0, cost=0, resources=9999)
        result = q.enqueue("CombatShip_S", build_time=10.0, cost=0, resources=9999)
        assert result is False

    def test_update_returns_none_before_done(self):
        q = BuildQueue()
        q.enqueue("CombatShip_S", build_time=10.0, cost=0, resources=9999)
        assert q.update(5.0) is None

    def test_update_returns_unit_type_when_done(self):
        q = BuildQueue()
        q.enqueue("CombatShip_S", build_time=10.0, cost=0, resources=9999)
        result = q.update(10.1)
        assert result == "CombatShip_S"

    def test_two_queues_advance_independently(self):
        q1 = BuildQueue()
        q2 = BuildQueue()
        q1.enqueue("CombatShip_S", build_time=5.0,  cost=0, resources=9999)
        q2.enqueue("CombatShip_L", build_time=70.0, cost=0, resources=9999)
        r1 = q1.update(5.1)
        r2 = q2.update(5.1)
        assert r1 == "CombatShip_S"
        assert r2 is None

    def test_second_item_starts_after_first_completes(self):
        q = BuildQueue()
        q.enqueue("CombatShip_S", build_time=5.0, cost=0, resources=9999)
        q.enqueue("CombatShip_S", build_time=5.0, cost=0, resources=9999)
        q.update(5.1)   # first done
        result = q.update(5.1)   # second done
        assert result == "CombatShip_S"

    def test_mothership_has_two_queues(self):
        ms = Mothership(pos=(0, 0), team=TEAM_PLAYER)
        assert len(ms.build_queues) == 2

    def test_empty_queue_update_returns_none(self):
        q = BuildQueue()
        assert q.update(1.0) is None


# ── BuildSystem state machine ─────────────────────────────────────

class TestBuilderShipStateMachine:
    def test_idle_builder_stays_idle_without_assignment(self):
        w = _world()
        ms = _mothership()
        b = _builder()
        w.add_entity(ms); w.add_entity(b)
        sys = BuildSystem()
        sys.update(w, 0.1)
        assert b.state == "IDLE"

    def test_builder_moves_to_site(self):
        w = _world()
        ms = _mothership()
        b = _builder(pos=(0, 0))
        w.add_entity(ms); w.add_entity(b)
        b.state = "MOVING_TO_SITE"
        b.assigned_target = pygame.Vector2(500, 0)
        b.building_type = "MiningStation"
        sys = BuildSystem()
        sys.update(w, 0.1)
        # Ship should have moved toward target
        assert b.pos.x > 0

    def test_builder_at_site_transitions_to_building(self):
        w = _world()
        ms = _mothership()
        b = _builder(pos=(10, 0))
        w.add_entity(ms); w.add_entity(b)
        b.state = "MOVING_TO_SITE"
        b.assigned_target = pygame.Vector2(10, 0)
        b.building_type = "MiningStation"
        sys = BuildSystem()
        sys.update(w, 0.0)
        assert b.state == "BUILDING"

    def test_building_progress_accumulates(self):
        w = _world()
        ms = _mothership()
        b = _builder(pos=(10, 0))
        w.add_entity(ms); w.add_entity(b)
        b.state = "BUILDING"
        b.assigned_target = pygame.Vector2(10, 0)
        b.building_type = "MiningStation"
        b._build_progress = 0.0
        sys = BuildSystem()
        sys.update(w, 1.0)
        assert b._build_progress == pytest.approx(1.0)

    def test_building_complete_adds_entity_to_world(self):
        from constants import STATION_BUILD_TIME
        w = _world()
        ms = _mothership()
        b = _builder(pos=(200, 0))
        w.add_entity(ms); w.add_entity(b)
        b.state = "BUILDING"
        b.assigned_target = pygame.Vector2(200, 0)
        b.building_type = "MiningStation"
        b._build_progress = STATION_BUILD_TIME - 0.01
        initial_count = len(w.entities)
        sys = BuildSystem()
        sys.update(w, 0.1)
        assert len(w.entities) > initial_count

    def test_building_complete_resets_builder_to_idle(self):
        from constants import STATION_BUILD_TIME
        w = _world()
        ms = _mothership()
        b = _builder(pos=(200, 0))
        w.add_entity(ms); w.add_entity(b)
        b.state = "BUILDING"
        b.assigned_target = pygame.Vector2(200, 0)
        b.building_type = "MiningStation"
        b._build_progress = STATION_BUILD_TIME - 0.01
        sys = BuildSystem()
        sys.update(w, 0.1)
        assert b.state == "IDLE"
        assert b.building_type is None

    def test_builder_destroyed_resets_progress(self):
        """If builder dies mid-construction, progress should be reset."""
        w = _world()
        ms = _mothership()
        b = _builder(pos=(200, 0))
        w.add_entity(ms); w.add_entity(b)
        b.state = "BUILDING"
        b.assigned_target = pygame.Vector2(200, 0)
        b.building_type = "MiningStation"
        b._build_progress = 5.0
        b.hp = 0   # builder dies
        sys = BuildSystem()
        sys.update(w, 0.1)
        assert b._build_progress == 0.0


# ── MiningStation auto-attach ─────────────────────────────────────

class TestMiningStationAutoAttach:
    def test_station_attaches_nearest_asteroid_within_radius(self):
        from constants import STATION_BUILD_TIME
        w = _world()
        ms = _mothership()
        ast = Asteroid(pos=(210, 0), size="M")   # within 150px of (200,0)
        b = _builder(pos=(200, 0))
        w.add_entity(ms); w.add_entity(ast); w.add_entity(b)
        b.state = "BUILDING"
        b.assigned_target = pygame.Vector2(200, 0)
        b.building_type = "MiningStation"
        b._build_progress = STATION_BUILD_TIME - 0.01
        sys = BuildSystem()
        sys.update(w, 0.1)
        # Find the newly placed station
        stations = [e for e in w.entities if isinstance(e, MiningStation)]
        assert len(stations) == 1
        assert stations[0].attached_asteroid is ast

    def test_station_no_asteroid_nearby_stays_unattached(self):
        from constants import STATION_BUILD_TIME
        w = _world()
        ms = _mothership()
        ast = Asteroid(pos=(500, 0), size="M")   # > 150px from (200,0)
        b = _builder(pos=(200, 0))
        w.add_entity(ms); w.add_entity(ast); w.add_entity(b)
        b.state = "BUILDING"
        b.assigned_target = pygame.Vector2(200, 0)
        b.building_type = "MiningStation"
        b._build_progress = STATION_BUILD_TIME - 0.01
        sys = BuildSystem()
        sys.update(w, 0.1)
        stations = [e for e in w.entities if isinstance(e, MiningStation)]
        assert stations[0].attached_asteroid is None
