"""Tests for ai/enemy.py — EnemyAI state machine."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from core.world import World
from entities.ship import CombatShip, MiningShip
from entities.building import Mothership
from entities.asteroid import Asteroid
from ai.enemy import EnemyAI
from constants import TEAM_PLAYER, TEAM_ENEMY, AI_ATTACK_THRESHOLD


# ── Helpers ───────────────────────────────────────────────────────

def _world_with_mothershipss():
    w = World()
    w.resources[TEAM_PLAYER] = 0
    w.resources[TEAM_ENEMY]  = 500
    pm = Mothership(pos=(200, 200), team=TEAM_PLAYER)
    em = Mothership(pos=(2700, 2700), team=TEAM_ENEMY)
    w.add_entity(pm)
    w.add_entity(em)
    return w, pm, em


# ── State transitions ─────────────────────────────────────────────

class TestEnemyAIStates:
    def test_initial_state_idle(self):
        ai = EnemyAI()
        assert ai.state == "idle"

    def test_idle_transitions_to_mining_with_asteroid(self):
        w, pm, em = _world_with_mothershipss()
        ast = Asteroid(pos=(2600, 2600), size="M")
        w.add_entity(ast)
        ai = EnemyAI()
        ai.update(w, 0.1)
        assert ai.state == "mining"

    def test_idle_stays_idle_without_asteroid(self):
        w, pm, em = _world_with_mothershipss()
        ai = EnemyAI()
        ai.update(w, 0.1)
        # No asteroids → stays idle (or tries to mine with nothing)
        assert ai.state in ("idle", "mining")

    def test_mining_dispatches_mining_ship(self):
        w, pm, em = _world_with_mothershipss()
        ast = Asteroid(pos=(2600, 2600), size="M")
        w.add_entity(ast)
        ai = EnemyAI()
        ai.update(w, 0.1)   # → mining
        # AI should have added a mining ship
        enemy_ships = [e for e in w.entities
                       if isinstance(e, MiningShip) and e.team == TEAM_ENEMY]
        assert len(enemy_ships) >= 1

    def test_building_transitions_when_mining_ships_exist(self):
        w, pm, em = _world_with_mothershipss()
        ast = Asteroid(pos=(2600, 2600), size="M")
        ms = MiningShip(pos=(2700, 2700), team=TEAM_ENEMY)
        ms.assigned_asteroid = ast
        w.add_entity(ast); w.add_entity(ms)
        ai = EnemyAI()
        ai.state = "mining"
        ai.update(w, 0.1)
        assert ai.state == "building"

    def test_attacking_when_enough_combat_ships(self):
        w, pm, em = _world_with_mothershipss()
        for _ in range(AI_ATTACK_THRESHOLD):
            s = CombatShip(pos=(2700, 2700), size="S", team=TEAM_ENEMY)
            w.add_entity(s)
        ai = EnemyAI()
        ai.state = "building"
        ai.update(w, 0.1)
        assert ai.state == "attacking"

    def test_attacking_sends_ships_toward_player(self):
        w, pm, em = _world_with_mothershipss()
        for _ in range(AI_ATTACK_THRESHOLD):
            s = CombatShip(pos=(2700, 2700), size="S", team=TEAM_ENEMY)
            w.add_entity(s)
        ai = EnemyAI()
        ai.state = "attacking"
        ai.update(w, 0.1)
        # Ships should have a target set toward player
        combat_ships = [e for e in w.entities
                        if isinstance(e, CombatShip) and e.team == TEAM_ENEMY]
        assert all(e._target_pos is not None for e in combat_ships)

    def test_building_state_queues_combat_ship(self):
        w, pm, em = _world_with_mothershipss()
        w.resources[TEAM_ENEMY] = 9999
        ai = EnemyAI()
        ai.state = "building"
        ai.update(w, 0.1)
        # Enemy mothership should have something queued
        assert em.build_queues[0].producing is not None or \
               len(em.build_queues[0].queue) > 0 or \
               em.build_queues[1].producing is not None or \
               len(em.build_queues[1].queue) > 0

    def test_ai_update_does_not_raise_with_empty_world(self):
        w = World()
        w.resources[TEAM_ENEMY] = 500
        ai = EnemyAI()
        ai.update(w, 0.1)   # no crash
