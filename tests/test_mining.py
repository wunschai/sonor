"""Tests for systems/mining.py — MiningSystem state machine."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from core.world import World
from entities.ship import MiningShip
from entities.building import Mothership, MiningStation
from entities.asteroid import Asteroid
from systems.mining import MiningSystem
from constants import (
    TEAM_PLAYER,
    MINE_RATE, CARGO_CAP,
    STATION_MINE_RATE, STATION_BUFFER_CAP, STATION_COLLECT_RADIUS,
)


# ── Helpers ───────────────────────────────────────────────────────

def _world():
    w = World()
    w.resources[TEAM_PLAYER] = 0
    return w


def _mothership(pos=(0, 0)):
    return Mothership(pos=pos, team=TEAM_PLAYER)


def _ship(pos=(0, 0)):
    s = MiningShip(pos=pos, team=TEAM_PLAYER)
    return s


def _asteroid(pos=(0, 0), size="M"):
    return Asteroid(pos=pos, size=size)


def _station(pos=(0, 0)):
    return MiningStation(pos=pos, team=TEAM_PLAYER)


# ── State machine transitions ────────────────────────────────────

class TestMiningShipStateMachine:
    def test_idle_ship_stays_idle_without_asteroid(self):
        w = _world()
        ms = Mothership(pos=(0, 0), team=TEAM_PLAYER)
        ship = _ship()
        w.add_entity(ms); w.add_entity(ship)
        sys = MiningSystem()
        sys.update(w, 0.1)
        assert ship.state == "IDLE"

    def test_assign_asteroid_triggers_moving_to_ast(self):
        w = _world()
        ms = Mothership(pos=(0, 0), team=TEAM_PLAYER)
        ship = _ship(pos=(0, 0))
        ast = _asteroid(pos=(200, 0))
        w.add_entity(ms); w.add_entity(ship); w.add_entity(ast)
        ship.assigned_asteroid = ast
        ship.state = "MOVING_TO_AST"
        sys = MiningSystem()
        sys.update(w, 0.1)
        assert ship.state == "MOVING_TO_AST"

    def test_ship_at_asteroid_transitions_to_mining(self):
        w = _world()
        ms = Mothership(pos=(0, 0), team=TEAM_PLAYER)
        ship = _ship(pos=(10, 0))   # very close to asteroid
        ast = _asteroid(pos=(10, 0))
        w.add_entity(ms); w.add_entity(ship); w.add_entity(ast)
        ship.assigned_asteroid = ast
        ship.state = "MOVING_TO_AST"
        sys = MiningSystem()
        sys.update(w, 0.0)
        assert ship.state == "MINING"
        assert ast.has_attached_ship()

    def test_mining_accumulates_cargo(self):
        w = _world()
        ms = Mothership(pos=(0, 0), team=TEAM_PLAYER)
        ship = _ship(pos=(10, 0))
        ast = _asteroid(pos=(10, 0))
        w.add_entity(ms); w.add_entity(ship); w.add_entity(ast)
        ship.state = "MINING"
        ship.assigned_asteroid = ast
        ast.attach(ship)
        sys = MiningSystem()
        sys.update(w, 1.0)
        assert ship.cargo == pytest.approx(MINE_RATE * 1.0)

    def test_cargo_full_triggers_moving_to_base(self):
        w = _world()
        ms = Mothership(pos=(0, 0), team=TEAM_PLAYER)
        ship = _ship(pos=(10, 0))
        ast = _asteroid(pos=(10, 0))
        w.add_entity(ms); w.add_entity(ship); w.add_entity(ast)
        ship.state = "MINING"
        ship.assigned_asteroid = ast
        ship.cargo = CARGO_CAP - 1
        ast.attach(ship)
        sys = MiningSystem()
        sys.update(w, 1.0)
        assert ship.state == "MOVING_TO_BASE"
        assert not ast.has_attached_ship()

    def test_ship_at_mothership_unloads(self):
        w = _world()
        ms = Mothership(pos=(0, 0), team=TEAM_PLAYER)
        ship = _ship(pos=(5, 0))   # at mothership
        w.add_entity(ms); w.add_entity(ship)
        ship.state = "MOVING_TO_BASE"
        ship.cargo = 80
        sys = MiningSystem()
        sys.update(w, 0.0)
        assert w.resources[TEAM_PLAYER] == 80
        assert ship.cargo == 0

    def test_unload_resets_to_idle_without_asteroid(self):
        w = _world()
        ms = Mothership(pos=(0, 0), team=TEAM_PLAYER)
        ship = _ship(pos=(5, 0))
        w.add_entity(ms); w.add_entity(ship)
        ship.state = "MOVING_TO_BASE"
        ship.cargo = 50
        ship.assigned_asteroid = None
        sys = MiningSystem()
        sys.update(w, 0.0)
        assert ship.state == "IDLE"

    def test_unload_resumes_mining_with_asteroid(self):
        w = _world()
        ms = Mothership(pos=(0, 0), team=TEAM_PLAYER)
        ship = _ship(pos=(5, 0))
        ast = _asteroid(pos=(200, 0))
        w.add_entity(ms); w.add_entity(ship); w.add_entity(ast)
        ship.state = "MOVING_TO_BASE"
        ship.cargo = 50
        ship.assigned_asteroid = ast
        sys = MiningSystem()
        sys.update(w, 0.0)
        assert ship.state == "MOVING_TO_AST"


# ── Station buffer ────────────────────────────────────────────────

class TestMiningStation:
    def test_station_mines_when_no_ship(self):
        w = _world()
        ast = _asteroid(pos=(100, 0))
        sta = _station(pos=(100, 0))
        sta.attached_asteroid = ast
        w.add_entity(ast); w.add_entity(sta)
        sys = MiningSystem()
        sys.update(w, 1.0)
        assert sta.buffer == pytest.approx(STATION_MINE_RATE * 1.0)

    def test_station_stops_when_ship_attached(self):
        w = _world()
        ast = _asteroid(pos=(100, 0))
        sta = _station(pos=(100, 0))
        sta.attached_asteroid = ast
        ship = _ship(pos=(100, 0))
        ship.state = "MINING"
        ship.assigned_asteroid = ast
        ast.attach(ship)
        w.add_entity(ast); w.add_entity(sta); w.add_entity(ship)
        sys = MiningSystem()
        sys.update(w, 1.0)
        assert sta.buffer == 0

    def test_station_buffer_caps_at_buffer_cap(self):
        w = _world()
        ast = _asteroid(pos=(100, 0))
        sta = _station(pos=(100, 0))
        sta.attached_asteroid = ast
        sta.buffer = STATION_BUFFER_CAP - 1
        w.add_entity(ast); w.add_entity(sta)
        sys = MiningSystem()
        sys.update(w, 10.0)   # would overflow without cap
        assert sta.buffer <= STATION_BUFFER_CAP

    def test_station_without_asteroid_does_not_mine(self):
        w = _world()
        sta = _station()
        sta.attached_asteroid = None
        w.add_entity(sta)
        sys = MiningSystem()
        sys.update(w, 1.0)
        assert sta.buffer == 0


# ── Station collection ────────────────────────────────────────────

class TestStationCollection:
    def test_ship_collects_from_nearby_station(self):
        w = _world()
        ms = Mothership(pos=(0, 0), team=TEAM_PLAYER)
        ast = _asteroid(pos=(500, 0))
        sta = _station(pos=(500, 0))
        sta.attached_asteroid = ast
        sta.buffer = 60
        ship = _ship(pos=(500 + STATION_COLLECT_RADIUS - 5, 0))
        ship.state = "MOVING_TO_BASE"
        w.add_entity(ms); w.add_entity(ast); w.add_entity(sta); w.add_entity(ship)
        sys = MiningSystem()
        sys.update(w, 0.0)
        # Ship should have collected from the station's buffer
        assert ship.cargo > 0 or w.resources[TEAM_PLAYER] > 0

    def test_ship_too_far_from_station_does_not_collect(self):
        w = _world()
        ms = Mothership(pos=(0, 0), team=TEAM_PLAYER)
        ast = _asteroid(pos=(500, 0))
        sta = _station(pos=(500, 0))
        sta.attached_asteroid = ast
        sta.buffer = 60
        ship = _ship(pos=(500 + STATION_COLLECT_RADIUS + 50, 0))
        ship.state = "MOVING_TO_BASE"
        w.add_entity(ms); w.add_entity(ast); w.add_entity(sta); w.add_entity(ship)
        initial_buffer = sta.buffer
        sys = MiningSystem()
        sys.update(w, 0.0)
        assert sta.buffer == initial_buffer
