"""MiningSystem — drives MiningShip state machines and MiningStation auto-mine."""
from __future__ import annotations
import pygame

from entities.ship import MiningShip
from entities.building import Mothership, MiningStation
from entities.asteroid import Asteroid
from constants import (
    TEAM_PLAYER,
    MINE_RATE, CARGO_CAP,
    STATION_MINE_RATE, STATION_BUFFER_CAP, STATION_COLLECT_RADIUS,
)

# How close a ship must be to an asteroid/mothership to "arrive"
_ARRIVE_DIST = 20.0


class MiningSystem:
    """Updates all MiningShip state machines and MiningStation buffers."""

    def update(self, world, dt: float) -> None:
        # Collect key entities once per frame
        motherships = [e for e in world.entities
                       if isinstance(e, Mothership) and e.team == TEAM_PLAYER]
        stations    = [e for e in world.entities if isinstance(e, MiningStation)]
        ships       = [e for e in world.entities
                       if isinstance(e, MiningShip) and e.team == TEAM_PLAYER]

        # ── Station auto-mine ─────────────────────────────────────
        for sta in stations:
            if sta.attached_asteroid is None:
                continue
            # Stop auto-mining if a ship is present at this asteroid
            if sta.attached_asteroid.has_attached_ship():
                continue
            sta.buffer = min(
                sta.buffer_cap,
                sta.buffer + sta.mine_rate * dt,
            )

        # ── Ship state machines ───────────────────────────────────
        for ship in ships:
            if ship.state == "IDLE":
                if ship.assigned_asteroid is not None:
                    ship.state = "MOVING_TO_AST"

            elif ship.state == "MOVING_TO_AST":
                self._move_toward(ship, ship.assigned_asteroid.pos, dt)
                if self._arrived(ship.pos, ship.assigned_asteroid.pos):
                    ship.assigned_asteroid.attach(ship)
                    ship.state = "MINING"

            elif ship.state == "MINING":
                # Check station collection while passing
                self._check_station_collect(ship, stations)
                # Mine
                mined = MINE_RATE * dt
                ship.cargo = min(ship.cargo_cap, ship.cargo + mined)
                if ship.cargo >= ship.cargo_cap:
                    # Detach and head home
                    ship.assigned_asteroid.detach(ship)
                    ship.state = "MOVING_TO_BASE"

            elif ship.state == "MOVING_TO_BASE":
                # Opportunistic station collection on the way home
                self._check_station_collect(ship, stations)
                # Move toward nearest friendly mothership
                ms = self._nearest_mothership(ship, motherships)
                if ms is None:
                    continue
                self._move_toward(ship, ms.pos, dt)
                if self._arrived(ship.pos, ms.pos):
                    self._unload(ship, world)

            elif ship.state == "COLLECTING_STATION":
                pass   # handled by check_station_collect; transition back inline

    # ── Sonar reveal ─────────────────────────────────────────────

    @staticmethod
    def reveal_by_hits(world, sonar_hits: list, radius: float = 40.0) -> None:
        """Mark asteroids as revealed if a SonarHit landed nearby."""
        asteroids = world.asteroids
        for hit in sonar_hits:
            hx, hy = hit.world_pos
            hit_pos = pygame.Vector2(hx, hy)
            for ast in asteroids:
                if ast.revealed:
                    continue
                if hit_pos.distance_to(ast.pos) <= radius:
                    ast.revealed = True

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _arrived(pos_a: pygame.Vector2, pos_b: pygame.Vector2) -> bool:
        return pos_a.distance_to(pos_b) <= _ARRIVE_DIST

    @staticmethod
    def _move_toward(ship: MiningShip, target: pygame.Vector2, dt: float) -> None:
        direction = target - ship.pos
        dist = direction.length()
        if dist < 1e-6:
            return
        spd = (ship.speed_mode.effective_speed(ship.speed)
               if hasattr(ship, "speed_mode") else ship.speed)
        step = spd * dt
        if step >= dist:
            ship.pos = pygame.Vector2(target)
        else:
            ship.pos += direction.normalize() * step

    @staticmethod
    def _nearest_mothership(ship: MiningShip, motherships: list):
        if not motherships:
            return None
        return min(motherships, key=lambda m: ship.pos.distance_to(m.pos))

    @staticmethod
    def _unload(ship: MiningShip, world) -> None:
        world.resources[ship.team] = world.resources.get(ship.team, 0) + int(ship.cargo)
        ship.cargo = 0
        if ship.assigned_asteroid is not None:
            ship.state = "MOVING_TO_AST"
        else:
            ship.state = "IDLE"

    @staticmethod
    def _check_station_collect(ship: MiningShip, stations: list) -> None:
        """Transfer station buffer to ship cargo when within collection radius."""
        for sta in stations:
            if sta.team != ship.team:
                continue
            if sta.buffer <= 0:
                continue
            dist = ship.pos.distance_to(sta.pos)
            if dist <= STATION_COLLECT_RADIUS:
                transferable = min(sta.buffer, ship.cargo_cap - ship.cargo)
                ship.cargo  += transferable
                sta.buffer  -= transferable
