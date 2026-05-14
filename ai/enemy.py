"""EnemyAI — simple state machine: idle → mining → building → attacking."""
from __future__ import annotations
import pygame

from entities.ship import CombatShip, MiningShip
from entities.building import Mothership
from entities.asteroid import Asteroid
from constants import (
    TEAM_ENEMY, TEAM_PLAYER,
    AI_ATTACK_THRESHOLD,
    SHIP_BUILD_TIME, SHIP_BUILD_COST,
    MINING_SHIP_COST,
)

_MINING_SHIP_BUILD_TIME = 15.0   # seconds


class EnemyAI:
    """
    State machine:
      idle     — waiting / no resources
      mining   — dispatching mining ship(s) to collect minerals
      building — queuing combat ships in mothership build queues
      attacking — sending all combat ships toward the player
    """

    def __init__(self):
        self.state = "idle"
        self._dispatched_miner = False

    def update(self, world, dt: float) -> None:
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
        asteroids = world.asteroids
        if asteroids:
            self.state = "mining"
            self._tick_mining(world, em)

    def _tick_mining(self, world, em) -> None:
        enemy_miners = [e for e in world.entities
                        if isinstance(e, MiningShip) and e.team == TEAM_ENEMY]
        if not enemy_miners:
            # Dispatch one mining ship
            ast = self._nearest_asteroid(em, world)
            miner = MiningShip(pos=em.pos, team=TEAM_ENEMY)
            if ast:
                miner.assigned_asteroid = ast
                miner.state = "MOVING_TO_AST"
            world.add_entity(miner)
        else:
            # Mining in progress → transition to building
            self.state = "building"

    def _tick_building(self, world, em) -> None:
        # Count enemy combat ships
        combat_ships = [e for e in world.entities
                        if isinstance(e, CombatShip) and e.team == TEAM_ENEMY]
        if len(combat_ships) >= AI_ATTACK_THRESHOLD:
            self.state = "attacking"
            return

        # Enqueue a combat ship if possible
        if em is not None:
            resources = world.resources.get(TEAM_ENEMY, 0)
            cost = SHIP_BUILD_COST["S"]
            for q in em.build_queues:
                if q.enqueue("CombatShip_S", SHIP_BUILD_TIME["S"], cost, resources):
                    world.resources[TEAM_ENEMY] = max(0, resources - cost)
                    break

    def _tick_attacking(self, world, em) -> None:
        player_ms = self._player_mothership(world)
        if player_ms is None:
            return
        target_pos = pygame.Vector2(player_ms.pos)
        for e in world.entities:
            if isinstance(e, CombatShip) and e.team == TEAM_ENEMY:
                e._target_pos = target_pos

    # ── Helpers ───────────────────────────────────────────────────

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

    @staticmethod
    def _nearest_asteroid(ref, world):
        if ref is None:
            return None
        asteroids = world.asteroids
        if not asteroids:
            return None
        return min(asteroids, key=lambda a: ref.pos.distance_to(a.pos))
