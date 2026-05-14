"""Tests for systems/combat.py — CombatSystem and win condition."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from core.world import World
from entities.ship import CombatShip
from entities.building import Mothership, Turret
from systems.combat import CombatSystem
from constants import (
    TEAM_PLAYER, TEAM_ENEMY,
    SHIP_DAMAGE, SHIP_FIRE_RATE, SHIP_ATTACK_RANGE, SHIP_HP,
    TURRET_DAMAGE, TURRET_FIRE_RATE, TURRET_ATTACK_RANGE,
)


# ── Helpers ───────────────────────────────────────────────────────

def _world():
    w = World()
    w.resources[TEAM_PLAYER] = 0
    w.resources[TEAM_ENEMY] = 0
    return w


def _combat(pos=(0, 0), size="S", team=TEAM_PLAYER):
    return CombatShip(pos=pos, size=size, team=team)


def _mothership(pos=(0, 0), team=TEAM_PLAYER):
    return Mothership(pos=pos, team=team)


# ── Auto-targeting ────────────────────────────────────────────────

class TestCombatSystemTargeting:
    def test_ship_in_range_fires(self):
        w = _world()
        attacker = _combat(pos=(0, 0), size="S", team=TEAM_PLAYER)
        target   = _combat(pos=(SHIP_ATTACK_RANGE["S"] - 10, 0), team=TEAM_ENEMY)
        w.add_entity(attacker); w.add_entity(target)
        sys = CombatSystem()
        # Advance enough time to get a shot off
        sys.update(w, 1.0 / SHIP_FIRE_RATE["S"] + 0.01)
        assert target.hp < SHIP_HP["S"]

    def test_ship_outside_range_does_not_fire(self):
        w = _world()
        attacker = _combat(pos=(0, 0), size="S", team=TEAM_PLAYER)
        target   = _combat(pos=(SHIP_ATTACK_RANGE["S"] + 50, 0), team=TEAM_ENEMY)
        w.add_entity(attacker); w.add_entity(target)
        sys = CombatSystem()
        sys.update(w, 10.0)
        assert target.hp == SHIP_HP["S"]

    def test_friendly_fire_does_not_occur(self):
        w = _world()
        a = _combat(pos=(0, 0), size="S", team=TEAM_PLAYER)
        b = _combat(pos=(10, 0), size="S", team=TEAM_PLAYER)
        w.add_entity(a); w.add_entity(b)
        sys = CombatSystem()
        sys.update(w, 10.0)
        assert b.hp == SHIP_HP["S"]

    def test_fire_rate_limits_shots(self):
        """Fire rate is shots/sec; ship should not fire faster than that."""
        w = _world()
        attacker = _combat(pos=(0, 0), size="S", team=TEAM_PLAYER)
        target   = _combat(pos=(10, 0), size="S", team=TEAM_ENEMY)
        w.add_entity(attacker); w.add_entity(target)
        sys = CombatSystem()
        # Slightly less than one shot period
        sys.update(w, 1.0 / SHIP_FIRE_RATE["S"] - 0.05)
        assert target.hp == SHIP_HP["S"]

    def test_damage_correct_for_size(self):
        w = _world()
        attacker = _combat(pos=(0, 0), size="M", team=TEAM_PLAYER)
        target   = _combat(pos=(10, 0), size="S", team=TEAM_ENEMY)
        w.add_entity(attacker); w.add_entity(target)
        sys = CombatSystem()
        sys.update(w, 1.0 / SHIP_FIRE_RATE["M"] + 0.01)
        assert target.hp == SHIP_HP["S"] - SHIP_DAMAGE["M"]

    def test_dead_units_removed_from_world(self):
        w = _world()
        attacker = _combat(pos=(0, 0), size="L", team=TEAM_PLAYER)
        target   = _combat(pos=(10, 0), size="S", team=TEAM_ENEMY)
        w.add_entity(attacker); w.add_entity(target)
        sys = CombatSystem()
        # Fire enough to kill a S ship (hp=100, damage=40 for L)
        for _ in range(5):
            sys.update(w, 1.0 / SHIP_FIRE_RATE["L"] + 0.01)
        assert target not in w.entities

    def test_turret_attacks_in_range(self):
        w = _world()
        turret = Turret(pos=(0, 0), team=TEAM_PLAYER)
        target = _combat(pos=(TURRET_ATTACK_RANGE - 10, 0), team=TEAM_ENEMY)
        w.add_entity(turret); w.add_entity(target)
        sys = CombatSystem()
        sys.update(w, 1.0 / TURRET_FIRE_RATE + 0.01)
        assert target.hp < SHIP_HP["S"]

    def test_attack_range_boundary(self):
        """Entity at exactly attack_range+1 should not be targeted."""
        w = _world()
        attacker = _combat(pos=(0, 0), size="S", team=TEAM_PLAYER)
        target   = _combat(pos=(SHIP_ATTACK_RANGE["S"] + 1, 0), team=TEAM_ENEMY)
        w.add_entity(attacker); w.add_entity(target)
        sys = CombatSystem()
        sys.update(w, 10.0)
        assert target.hp == SHIP_HP["S"]


# ── Win condition ─────────────────────────────────────────────────

class TestWinCondition:
    def test_no_result_when_both_mothershipss_alive(self):
        w = _world()
        w.add_entity(_mothership(pos=(0, 0), team=TEAM_PLAYER))
        w.add_entity(_mothership(pos=(2700, 2700), team=TEAM_ENEMY))
        assert w.check_win_condition() is None

    def test_player_wins_when_enemy_mothership_dead(self):
        w = _world()
        pm = _mothership(pos=(0, 0), team=TEAM_PLAYER)
        em = _mothership(pos=(2700, 2700), team=TEAM_ENEMY)
        em.hp = 0
        w.add_entity(pm); w.add_entity(em)
        assert w.check_win_condition() == "player_win"

    def test_player_loses_when_player_mothership_dead(self):
        w = _world()
        pm = _mothership(pos=(0, 0), team=TEAM_PLAYER)
        em = _mothership(pos=(2700, 2700), team=TEAM_ENEMY)
        pm.hp = 0
        w.add_entity(pm); w.add_entity(em)
        assert w.check_win_condition() == "player_lose"

    def test_no_motherships_returns_none(self):
        w = _world()
        assert w.check_win_condition() is None

    def test_only_player_mothership_alive_wins(self):
        """Enemy mothership fully destroyed (removed from world) → player wins."""
        w = _world()
        w.add_entity(_mothership(pos=(0, 0), team=TEAM_PLAYER))
        # Enemy mothership not added at all
        assert w.check_win_condition() == "player_win"
