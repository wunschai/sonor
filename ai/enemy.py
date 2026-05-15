"""EnemyAI — layered state machine with multi-mining, defence, and turret building."""
from __future__ import annotations
import pygame

from entities.ship import CombatShip, MiningShip, BuilderShip
from entities.building import Mothership, MiningStation, Turret
from entities.asteroid import Asteroid
from constants import (
    TEAM_ENEMY, TEAM_PLAYER,
    AI_ATTACK_THRESHOLD,
    SHIP_BUILD_TIME, SHIP_BUILD_COST,
    MINING_SHIP_COST, BUILDER_SHIP_COST,
)

_MAX_MINERS       = 3      # max simultaneous mining ships
_DEFENDER_COUNT   = 2      # combat ships kept near mothership during attack
_TURRET_GUARD_R   = 200.0  # px — turret counts as guarding a station within this radius
_MINING_SHIP_BUILD_TIME = 15.0


class EnemyAI:
    """
    State machine:
      idle      — startup delay / waiting for resources
      mining    — dispatching up to _MAX_MINERS ships across different asteroids
      building  — dynamic ship production + maintain mining + turret construction
      attacking — split force: _DEFENDER_COUNT stay back, rest assault player
    """

    def __init__(self):
        self.state = "idle"
        self._startup_timer = 60.0

    def update(self, world, dt: float) -> None:
        if self._startup_timer > 0:
            self._startup_timer -= dt
            return

        em = self._enemy_mothership(world)

        if self.state == "idle":
            self._tick_idle(world, em)
        elif self.state == "mining":
            self._tick_mining(world, em)
        elif self.state == "building":
            self._tick_building(world, em)
        elif self.state == "attacking":
            self._tick_attacking(world, em)

    # ── State handlers ────────────────────────────────────────────

    def _tick_idle(self, world, em) -> None:
        if world.asteroids:
            self.state = "mining"
            self._tick_mining(world, em)

    def _tick_mining(self, world, em) -> None:
        if em is None:
            return
        existing = [e for e in world.entities
                    if isinstance(e, MiningShip) and e.team == TEAM_ENEMY]
        if existing:
            self.state = "building"
            return
        self._dispatch_miners(world, em)

    def _tick_building(self, world, em) -> None:
        self._maintain_mining(world, em)
        self._maybe_build_turret(world, em)

        combat_ships = [e for e in world.entities
                        if isinstance(e, CombatShip) and e.team == TEAM_ENEMY]
        if len(combat_ships) >= AI_ATTACK_THRESHOLD:
            self.state = "attacking"
            return

        if em is None:
            return
        resources = world.resources.get(TEAM_ENEMY, 0)
        size, cost, btime = self._choose_ship(resources)
        if cost <= resources:
            for q in sorted(em.build_queues,
                            key=lambda q: (1 if q.producing else 0) + len(q.queue)):
                if q.enqueue(f"CombatShip_{size}", btime, cost, resources):
                    world.resources[TEAM_ENEMY] = max(0, resources - cost)
                    break

    def _tick_attacking(self, world, em) -> None:
        player_ms = self._player_mothership(world)
        if player_ms is None:
            return

        # Continue economy even during attack
        self._maintain_mining(world, em)

        combat_ships = [e for e in world.entities
                        if isinstance(e, CombatShip) and e.team == TEAM_ENEMY]

        # Split: closest to own base → defenders, rest → attackers
        if em is not None:
            by_dist = sorted(combat_ships, key=lambda s: s.pos.distance_to(em.pos))
            defenders = by_dist[:_DEFENDER_COUNT]
            attackers = by_dist[_DEFENDER_COUNT:]
        else:
            defenders, attackers = [], combat_ships

        target = pygame.Vector2(player_ms.pos)
        for s in attackers:
            s._target_pos = target
        if em is not None:
            guard = pygame.Vector2(em.pos)
            for s in defenders:
                if s._target_pos is None or s.pos.distance_to(em.pos) > 200:
                    s._target_pos = guard

    # ── Economy helpers ───────────────────────────────────────────

    def _dispatch_miners(self, world, em) -> None:
        """Send miners to unoccupied asteroids, up to _MAX_MINERS."""
        if em is None:
            return
        existing = [e for e in world.entities
                    if isinstance(e, MiningShip) and e.team == TEAM_ENEMY]
        occupied = {m.assigned_asteroid for m in existing if m.assigned_asteroid}
        free_asts = sorted(
            (a for a in world.asteroids if a not in occupied),
            key=lambda a: a.pos.distance_to(em.pos),
        )
        resources = world.resources.get(TEAM_ENEMY, 0)

        for ast in free_asts:
            if len(existing) >= _MAX_MINERS:
                break
            if resources < MINING_SHIP_COST:
                break
            miner = MiningShip(pos=(em.pos.x, em.pos.y), team=TEAM_ENEMY)
            miner.assigned_asteroid = ast
            miner.state = "MOVING_TO_AST"
            world.add_entity(miner)
            world.resources[TEAM_ENEMY] = resources - MINING_SHIP_COST
            resources = world.resources[TEAM_ENEMY]
            existing.append(miner)

    def _maintain_mining(self, world, em) -> None:
        """Replace lost miners and fill up to _MAX_MINERS."""
        self._dispatch_miners(world, em)

    def _maybe_build_turret(self, world, em) -> None:
        """If an enemy MiningStation has no nearby turret, dispatch a BuilderShip."""
        if em is None:
            return
        builders = [e for e in world.entities
                    if isinstance(e, BuilderShip) and e.team == TEAM_ENEMY]
        if builders:
            return   # one builder at a time

        stations = [e for e in world.entities
                    if isinstance(e, MiningStation) and e.team == TEAM_ENEMY]
        turrets  = [e for e in world.entities
                    if isinstance(e, Turret) and e.team == TEAM_ENEMY]

        for st in stations:
            guarded = any(t.pos.distance_to(st.pos) <= _TURRET_GUARD_R for t in turrets)
            if guarded:
                continue
            resources = world.resources.get(TEAM_ENEMY, 0)
            if resources < BUILDER_SHIP_COST:
                return
            builder = BuilderShip(pos=(em.pos.x, em.pos.y), team=TEAM_ENEMY)
            turret_pos = pygame.Vector2(st.pos.x + 90, st.pos.y)
            builder.assigned_target = turret_pos
            builder.building_type   = "Turret"
            builder.state           = "MOVING_TO_SITE"
            world.add_entity(builder)
            world.resources[TEAM_ENEMY] = resources - BUILDER_SHIP_COST
            break

    @staticmethod
    def _choose_ship(resources: int) -> tuple[str, int, float]:
        """Return (size, cost, build_time) based on available resources."""
        if resources >= SHIP_BUILD_COST["L"]:
            return "L", SHIP_BUILD_COST["L"], SHIP_BUILD_TIME["L"]
        if resources >= SHIP_BUILD_COST["M"]:
            return "M", SHIP_BUILD_COST["M"], SHIP_BUILD_TIME["M"]
        return "S", SHIP_BUILD_COST["S"], SHIP_BUILD_TIME["S"]

    # ── Entity lookups ────────────────────────────────────────────

    @staticmethod
    def _enemy_mothership(world):
        for e in world.entities:
            if isinstance(e, Mothership) and e.team == TEAM_ENEMY:
                return e
        return None

    @staticmethod
    def _player_mothership(world):
        for e in world.entities:
            if isinstance(e, Mothership) and e.team == TEAM_PLAYER:
                return e
        return None
