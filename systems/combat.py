"""CombatSystem — auto-targeting and damage resolution."""
from __future__ import annotations
import pygame

from entities.ship import CombatShip
from entities.building import Turret


class CombatSystem:
    """Each frame: find targets, apply fire-rate timer, deal damage, remove dead."""

    def update(self, world, dt: float) -> list:
        """
        Advance all combat timers and resolve damage.
        Returns list of entities killed this frame.
        """
        combatants = [e for e in world.entities
                      if isinstance(e, (CombatShip, Turret))]
        dead = []

        for attacker in combatants:
            target = self._find_target(attacker, world)
            if target is None:
                continue

            # Advance fire timer
            attacker._fire_timer -= dt
            if attacker._fire_timer > 0:
                continue

            # Fire
            attacker._fire_timer = 1.0 / attacker.fire_rate
            killed = target.take_damage(attacker.damage)
            target._hit_flash = 0.3
            if killed and target not in dead:
                dead.append(target)

        # Remove dead entities
        for e in dead:
            world.remove_entity(e)

        return dead

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _find_target(attacker, world):
        """Return the nearest enemy entity within attack range, or None."""
        best     = None
        best_dist = attacker.attack_range + 1
        for e in world.entities:
            if not hasattr(e, "team") or e.team == attacker.team:
                continue
            if not hasattr(e, "hp") or e.hp <= 0:
                continue
            dist = attacker.pos.distance_to(e.pos)
            if dist <= attacker.attack_range and dist < best_dist:
                best_dist = dist
                best = e
        return best
