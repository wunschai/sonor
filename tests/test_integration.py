"""Headless integration tests for the Sonor game loop.

SDL_VIDEODRIVER and SDL_AUDIODRIVER are set to "dummy" by conftest.py before
any import of pygame occurs.  A single pygame.init() + display at module level
avoids repeated init overhead and satisfies pygame.font.SysFont calls made
inside various __init__ methods.
"""
import os
import pygame
import pytest

# ── one-time pygame bootstrap ─────────────────────────────────────
pygame.init()
pygame.display.set_mode((1, 1))

# ── project imports (after pygame is up) ─────────────────────────
from constants import (
    TEAM_PLAYER, TEAM_ENEMY,
    MAP_WIDTH, MAP_HEIGHT,
)
from core.world import World
from core.fog import FogMap
from core.sonar import ActivePulse, PassiveDetector
from ui.sonar_fx import SonarFX
from entities.ship import CombatShip, MiningShip, BuilderShip
from entities.building import Mothership
from entities.asteroid import Asteroid
from systems.mining import MiningSystem
from systems.build import BuildSystem
from systems.combat import CombatSystem
from ai.enemy import EnemyAI


# ══════════════════════════════════════════════════════════════════
# Game runner helper
# ══════════════════════════════════════════════════════════════════

def run_game(world: World, n_frames: int, dt: float = 1 / 60) -> object:
    """Simulate n_frames of the main game loop (headless).

    Mirrors the update logic in main.py:
      - CombatShip / generic unit movement via _target_pos
      - MiningSystem, BuildSystem, CombatSystem, EnemyAI
      - Mothership build_queue ticks + CombatShip spawn
      - FogMap update + reveal_asteroids
      - PassiveDetector + ActivePulse sonar hit check

    Returns the final result of world.check_win_condition().
    """
    fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
    sonar_fx = SonarFX()
    enemy_ai = EnemyAI()

    mining_sys = MiningSystem()
    build_sys = BuildSystem()
    combat_sys = CombatSystem()
    passive = PassiveDetector()

    for _ in range(n_frames):
        # ── Unit movement (CombatShip and other _target_pos holders) ─
        for e in world.entities:
            if isinstance(e, (MiningShip, BuilderShip)):
                continue   # handled by their systems
            if hasattr(e, "_target_pos") and e._target_pos is not None:
                spd = (e.speed_mode.effective_speed(e.speed)
                       if hasattr(e, "speed_mode") else e.speed)
                direction = e._target_pos - e.pos
                dist = direction.length()
                if dist < spd * dt:
                    e.pos = pygame.Vector2(e._target_pos)
                    e._target_pos = None
                    if hasattr(e, "state"):
                        e.state = "IDLE"
                else:
                    e.pos += direction.normalize() * spd * dt

        # ── Game systems ─────────────────────────────────────────────
        mining_sys.update(world, dt)
        build_sys.update(world, dt)
        combat_sys.update(world, dt)
        enemy_ai.update(world, dt)

        # ── Mothership build queues ───────────────────────────────────
        for e in list(world.entities):
            if not isinstance(e, Mothership):
                continue
            for q in e.build_queues:
                result = q.update(dt)
                if result is None:
                    continue
                spawn_pos = (e.pos.x + 40, e.pos.y + 40)
                if result == "CombatShip_S":
                    world.add_entity(CombatShip(pos=spawn_pos, size="S", team=e.team))
                elif result == "CombatShip_M":
                    world.add_entity(CombatShip(pos=spawn_pos, size="M", team=e.team))
                elif result == "CombatShip_L":
                    world.add_entity(CombatShip(pos=spawn_pos, size="L", team=e.team))

        # ── Fog update ────────────────────────────────────────────────
        player_units = world.entities_for_team(TEAM_PLAYER)
        fog.update(player_units)
        fog.reveal_asteroids(world.asteroids)

        # ── Sonar update ──────────────────────────────────────────────
        sonar_hits = []

        for e in world.entities:
            if not hasattr(e, "sonar"):
                continue
            if e.sonar.update(dt):
                strength = getattr(e, "sonar_strength", 1)
                pulse = ActivePulse(origin=(e.pos.x, e.pos.y), strength=strength)
                sonar_fx.add_pulse(pulse)

        all_entities = list(world.entities)
        for pulse in sonar_fx.pulses:
            hits = pulse.check_hit(all_entities)
            for h in hits:
                sonar_fx.add_hit(h)
                sonar_hits.append(h)
        sonar_fx.update(dt)

        enemy_units = world.entities_for_team(TEAM_ENEMY)
        passive_hits = passive.detect(player_units, enemy_units, dt)
        for h in passive_hits:
            sonar_fx.add_hit(h)
            sonar_hits.append(h)

        mining_sys.reveal_by_hits(world, sonar_hits)

    return world.check_win_condition()


# ══════════════════════════════════════════════════════════════════
# World builder helpers
# ══════════════════════════════════════════════════════════════════

def _make_standard_world() -> World:
    """Mirrors build_test_world() from main.py."""
    import random
    w = World()
    w.resources[TEAM_PLAYER] = 500

    pm = Mothership(pos=(300, 300), team=TEAM_PLAYER)
    w.add_entity(pm)
    for i in range(3):
        w.add_entity(CombatShip(pos=(320 + i * 30, 340), size="S", team=TEAM_PLAYER))
    w.add_entity(MiningShip(pos=(280, 360), team=TEAM_PLAYER))
    w.add_entity(BuilderShip(pos=(260, 360), team=TEAM_PLAYER))

    em = Mothership(pos=(2700, 2700), team=TEAM_ENEMY)
    w.add_entity(em)
    for i in range(2):
        w.add_entity(CombatShip(pos=(2720 + i * 30, 2720), size="M", team=TEAM_ENEMY))

    random.seed(42)
    for _ in range(12):
        pos = (random.randint(200, MAP_WIDTH - 200),
               random.randint(200, MAP_HEIGHT - 200))
        size = random.choice(("S", "M", "L"))
        w.add_entity(Asteroid(pos=pos, size=size))

    return w


# ══════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════

class TestSmoke:
    """Test 1: smoke test — 600 frames without crashing."""

    def test_standard_world_runs_10_seconds_without_exception(self):
        world = _make_standard_world()
        # Should complete without raising any exception
        run_game(world, n_frames=600, dt=1 / 60)


class TestMining:
    """Test 2: mining end-to-end — resources increase after a run."""

    def test_mining_ship_delivers_ore_to_mothership(self):
        w = World()
        w.resources[TEAM_PLAYER] = 0

        ms = Mothership(pos=(300, 300), team=TEAM_PLAYER)
        w.add_entity(ms)

        miner = MiningShip(pos=(320, 320), team=TEAM_PLAYER)
        w.add_entity(miner)

        asteroid = Asteroid(pos=(350, 350), size="S")
        w.add_entity(asteroid)

        # Pre-assign: miner is heading to the asteroid
        miner.assigned_asteroid = asteroid
        miner.state = "MOVING_TO_AST"

        initial_resources = w.resources[TEAM_PLAYER]

        # ~10.5 seconds: miner fills cargo (~613 frames) then travels home (~20 more)
        # Use 800 frames (~13 seconds) to give a comfortable margin
        run_game(w, n_frames=800, dt=1 / 60)

        assert w.resources[TEAM_PLAYER] > initial_resources, (
            f"Expected resources to increase; got {w.resources[TEAM_PLAYER]}"
        )


class TestCombat:
    """Test 3: CombatShip kills an adjacent target."""

    def test_one_ship_is_removed_from_world_after_combat(self):
        w = World()
        w.resources[TEAM_PLAYER] = 0

        # Give player enough resources so world stays valid
        player_ms = Mothership(pos=(300, 300), team=TEAM_PLAYER)
        w.add_entity(player_ms)
        enemy_ms = Mothership(pos=(2700, 2700), team=TEAM_ENEMY)
        w.add_entity(enemy_ms)

        # Place two CombatShip_S adjacent (distance 10px, attack_range=150px)
        player_ship = CombatShip(pos=(300, 300), size="S", team=TEAM_PLAYER)
        enemy_ship = CombatShip(pos=(310, 300), size="S", team=TEAM_ENEMY)
        w.add_entity(player_ship)
        w.add_entity(enemy_ship)

        # S ship: HP=100, damage=10, fire_rate=3 → ~3.3 seconds to kill
        # Run 5 seconds to be safe
        run_game(w, n_frames=300, dt=1 / 60)

        combat_ships = [e for e in w.entities if isinstance(e, CombatShip)]
        player_combat = [e for e in combat_ships if e.team == TEAM_PLAYER]
        enemy_combat = [e for e in combat_ships if e.team == TEAM_ENEMY]

        # At least one side's CombatShip should be dead/removed
        assert len(player_combat) == 0 or len(enemy_combat) == 0, (
            f"Expected one side eliminated; player={len(player_combat)}, "
            f"enemy={len(enemy_combat)}"
        )


class TestEnemyAI:
    """Test 4: EnemyAI state machine advances from idle."""

    def test_ai_transitions_away_from_idle_within_5_seconds(self):
        w = _make_standard_world()

        fog = FogMap(MAP_WIDTH, MAP_HEIGHT)
        sonar_fx = SonarFX()
        enemy_ai = EnemyAI()

        mining_sys = MiningSystem()
        build_sys = BuildSystem()
        combat_sys = CombatSystem()
        passive = PassiveDetector()

        enemy_ai._startup_timer = 0   # bypass startup delay for integration test
        assert enemy_ai.state == "idle"
        states_seen = {"idle"}

        dt = 1 / 60
        for _ in range(300):  # 5 seconds
            # Movement
            for e in w.entities:
                if isinstance(e, (MiningShip, BuilderShip)):
                    continue
                if hasattr(e, "_target_pos") and e._target_pos is not None:
                    spd = (e.speed_mode.effective_speed(e.speed)
                           if hasattr(e, "speed_mode") else e.speed)
                    direction = e._target_pos - e.pos
                    dist = direction.length()
                    if dist < spd * dt:
                        e.pos = pygame.Vector2(e._target_pos)
                        e._target_pos = None
                    else:
                        e.pos += direction.normalize() * spd * dt

            mining_sys.update(w, dt)
            build_sys.update(w, dt)
            combat_sys.update(w, dt)
            enemy_ai.update(w, dt)
            states_seen.add(enemy_ai.state)

            for e in list(w.entities):
                if not isinstance(e, Mothership):
                    continue
                for q in e.build_queues:
                    result = q.update(dt)
                    if result is None:
                        continue
                    spawn_pos = (e.pos.x + 40, e.pos.y + 40)
                    if result == "CombatShip_S":
                        w.add_entity(CombatShip(pos=spawn_pos, size="S", team=e.team))

            player_units = w.entities_for_team(TEAM_PLAYER)
            fog.update(player_units)
            fog.reveal_asteroids(w.asteroids)

        assert len(states_seen) > 1, (
            f"EnemyAI never left idle; states seen: {states_seen}"
        )
        assert "idle" not in states_seen or len(states_seen) > 1, (
            "AI should have advanced to at least 'mining'"
        )
        assert any(s != "idle" for s in states_seen), (
            f"AI stayed in idle for all 300 frames; states={states_seen}"
        )


class TestMothershipBuildQueue:
    """Test 5: Mothership build_queue produces a CombatShip."""

    def test_build_queue_spawns_combat_ship_after_build_time(self):
        w = World()
        w.resources[TEAM_PLAYER] = 1000

        ms = Mothership(pos=(300, 300), team=TEAM_PLAYER)
        w.add_entity(ms)

        # Enemy mothership so win condition doesn't trigger early
        em = Mothership(pos=(2700, 2700), team=TEAM_ENEMY)
        w.add_entity(em)

        # Enqueue with short build_time=2.0s so 3 seconds (180 frames) is enough
        enqueued = ms.build_queues[0].enqueue("CombatShip_S", 2.0, 100, w.resources[TEAM_PLAYER])
        assert enqueued, "enqueue() returned False — check resources/queue capacity"

        combat_before = [e for e in w.entities
                         if isinstance(e, CombatShip) and e.team == TEAM_PLAYER]
        count_before = len(combat_before)

        run_game(w, n_frames=180, dt=1 / 60)

        combat_after = [e for e in w.entities
                        if isinstance(e, CombatShip) and e.team == TEAM_PLAYER]
        assert len(combat_after) > count_before, (
            f"Expected a new CombatShip; before={count_before}, after={len(combat_after)}"
        )
        assert combat_after[-1].team == TEAM_PLAYER


class TestWinCondition:
    """Test 6: win condition triggers when enemy mothership is destroyed."""

    def test_player_wins_when_enemy_mothership_hp_is_1(self):
        w = World()
        w.resources[TEAM_PLAYER] = 0

        player_ms = Mothership(pos=(300, 300), team=TEAM_PLAYER)
        w.add_entity(player_ms)

        enemy_ms = Mothership(pos=(310, 300), team=TEAM_ENEMY)
        enemy_ms.hp = 1   # one shot away from death
        w.add_entity(enemy_ms)

        # Player CombatShip adjacent to enemy mothership (within attack_range=150)
        attacker = CombatShip(pos=(300, 300), size="S", team=TEAM_PLAYER)
        w.add_entity(attacker)

        # Run enough frames for at least one shot to land
        result = run_game(w, n_frames=120, dt=1 / 60)

        assert result == "player_win", (
            f"Expected 'player_win'; got {result!r}"
        )


class TestMovementCommand:
    """Test 7: right-click movement — CombatShip moves to target position."""

    def test_combat_ship_reaches_target_position_within_300_frames(self):
        w = World()
        w.resources[TEAM_PLAYER] = 0

        # Motherships to avoid win/lose triggers
        player_ms = Mothership(pos=(300, 300), team=TEAM_PLAYER)
        w.add_entity(player_ms)
        enemy_ms = Mothership(pos=(2700, 2700), team=TEAM_ENEMY)
        w.add_entity(enemy_ms)

        ship = CombatShip(pos=(300, 300), size="S", team=TEAM_PLAYER)
        w.add_entity(ship)

        target = pygame.Vector2(500, 500)
        ship._target_pos = target

        run_game(w, n_frames=300, dt=1 / 60)

        dist = ship.pos.distance_to(target)
        assert dist < 20, (
            f"Ship did not reach target; distance={dist:.1f}px (expected <20)"
        )
