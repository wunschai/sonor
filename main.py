"""Sonor — entry point and main game loop."""
import pygame
import sys
import random

from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, MAP_WIDTH, MAP_HEIGHT, FPS,
    CAMERA_SPEED, CAMERA_EDGE_MARGIN,
    TEAM_PLAYER, TEAM_ENEMY,
    COL_BLACK, COL_PLAYER, COL_ENEMY, COL_ASTEROID, COL_HUD_BG,
)
from core.world import World
from core.fog import FogMap
from core.render_filter import should_draw_entity
from core.sonar import ActivePulse, PassiveDetector
from entities.ship import CombatShip, MiningShip, BuilderShip
from entities.building import Mothership, Turret, MiningStation
from entities.asteroid import Asteroid
from ui.sonar_fx import SonarFX
from ui.minimap import Minimap
from ui.control_panel import ControlPanel
from systems.mining import MiningSystem
from systems.build import BuildSystem
from systems.combat import CombatSystem
from systems.collision import resolve_separation, formation_offsets
from ai.enemy import EnemyAI


# ── Unit Roster (left panel) ──────────────────────────────────────

class UnitRoster:
    """Left-side scrollable list of all player units."""

    PANEL_W = 180
    ROW_H   = 28

    # Short abbreviations for entity types
    _ABBREV = {
        "Mothership":    "MS",
        "CombatShip":    None,   # handled per-size below
        "MiningShip":    "MN",
        "BuilderShip":   "BD",
        "Turret":        "TU",
        "MiningStation": "ST",
    }

    def __init__(self, panel_y_start: int = 0, panel_h: int = 0):
        self._scroll          = 0
        self._panel_y         = panel_y_start
        self._panel_h         = panel_h
        self._font            = pygame.font.SysFont("monospace", 12)
        self._last_click_idx  = -1
        self._last_click_tick = 0
        self.camera_jump      = None   # set to entity on double-click

    # ── helpers ───────────────────────────────────────────────────

    @staticmethod
    def _abbrev(entity) -> str:
        name = type(entity).__name__
        if name == "CombatShip":
            size = getattr(entity, "size", "S")
            return f"CS-{size}"
        return UnitRoster._ABBREV.get(name, "??")

    def _player_units(self, world):
        return [e for e in world.entities
                if not isinstance(e, Asteroid)
                and hasattr(e, "team") and e.team == TEAM_PLAYER]

    def _grouped_rows(self, world):
        """Return a flat list mixing string headers and entity objects."""
        from entities.ship import CombatShip, MiningShip, BuilderShip
        from entities.building import Mothership, MiningStation, Turret
        all_units = self._player_units(world)
        ships     = [e for e in all_units
                     if isinstance(e, (CombatShip, MiningShip, BuilderShip))]
        buildings = [e for e in all_units
                     if isinstance(e, (Mothership, MiningStation, Turret))]
        rows = []
        if ships:
            rows.append("Ships")
            rows.extend(ships)
        if buildings:
            rows.append("Buildings")
            rows.extend(buildings)
        return rows

    def in_roster(self, screen_pos) -> bool:
        x, y = screen_pos
        return (0 <= x < self.PANEL_W
                and self._panel_y <= y < self._panel_y + self._panel_h)

    # ── draw ──────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, world, selection: list) -> None:
        rows = self._grouped_rows(world)
        if not rows:
            return

        # semi-transparent background
        bg = pygame.Surface((self.PANEL_W, self._panel_h), pygame.SRCALPHA)
        bg.fill((10, 12, 20, 200))
        surface.blit(bg, (0, self._panel_y))

        visible = self._panel_h // self.ROW_H
        start   = max(0, min(self._scroll, max(0, len(rows) - visible)))
        self._scroll = start

        for i, row in enumerate(rows[start: start + visible]):
            ry = self._panel_y + i * self.ROW_H

            if isinstance(row, str):
                # Group header
                pygame.draw.rect(surface, (15, 20, 35),
                                 (0, ry, self.PANEL_W, self.ROW_H - 1))
                hdr = self._font.render(f"── {row} ──", True, (100, 130, 170))
                surface.blit(hdr, (4, ry + 6))
                continue

            entity  = row
            selected = entity in selection
            row_col  = (40, 80, 130) if selected else (20, 25, 35)
            pygame.draw.rect(surface, row_col,
                             (0, ry, self.PANEL_W, self.ROW_H - 1))

            # abbreviation text
            abbrev = self._abbrev(entity)
            lbl    = self._font.render(abbrev, True, (210, 215, 220))
            surface.blit(lbl, (4, ry + 4))

            # HP bar (20 px wide, right side)
            bar_x = self.PANEL_W - 24
            bar_y = ry + 6
            bar_w = 20
            bar_h = 8
            if hasattr(entity, "hp") and hasattr(entity, "max_hp") and entity.max_hp > 0:
                ratio = max(0.0, entity.hp / entity.max_hp)
                pygame.draw.rect(surface, (120, 0, 0),   (bar_x, bar_y, bar_w, bar_h))
                pygame.draw.rect(surface, (0, 180, 0),   (bar_x, bar_y, int(bar_w * ratio), bar_h))
                pygame.draw.rect(surface, (80, 80, 80),  (bar_x, bar_y, bar_w, bar_h), 1)

            # state text (small, middle area)
            state = getattr(entity, "state", None)
            if state:
                st_lbl = self._font.render(str(state)[:8], True, (140, 160, 140))
                surface.blit(st_lbl, (50, ry + 4))

    # ── click ─────────────────────────────────────────────────────

    def handle_click(self, screen_pos, world, selection: list,
                     shift_held: bool) -> list:
        rows = self._grouped_rows(world)
        x, y = screen_pos
        if not (0 <= x < self.PANEL_W):
            return selection
        row_i = self._scroll + (y - self._panel_y) // self.ROW_H
        if row_i < 0 or row_i >= len(rows):
            return selection
        item = rows[row_i]
        if isinstance(item, str):
            return selection   # clicked a header — no-op

        clicked = item
        # Double-click detection (within 400 ms on same entity)
        now = pygame.time.get_ticks()
        if self._last_click_idx == row_i and now - self._last_click_tick < 400:
            self.camera_jump = clicked
        self._last_click_idx  = row_i
        self._last_click_tick = now

        if shift_held:
            if clicked in selection:
                return [e for e in selection if e is not clicked]
            return selection + [clicked]
        return [clicked]


# ── Render helpers ────────────────────────────────────────────────

_UNIT_COLOURS = {
    "Mothership":    (0, 220, 160),
    "CombatShip":   COL_PLAYER,
    "MiningShip":   (120, 220, 255),
    "BuilderShip":  (255, 220, 80),
    "Turret":       (200, 80,  200),
    "MiningStation":(80,  200, 80),
    "Asteroid":     COL_ASTEROID,
}
_UNIT_RADII = {"S": 8, "M": 12, "L": 18, "X": 6}


def _colour_of(entity):
    name = type(entity).__name__
    if hasattr(entity, "team") and entity.team == TEAM_ENEMY:
        return COL_ENEMY
    return _UNIT_COLOURS.get(name, (200, 200, 200))


def _radius_of(entity):
    if isinstance(entity, Asteroid):
        return {"S": 6, "M": 10, "L": 16}.get(entity.size, 8)
    size = getattr(entity, "size", "S")
    return _UNIT_RADII.get(size, 8)


def _draw_unit_bars(surface, entity, sx, sy, radius):
    """Draw HP bar (and cargo bar for mining ships) above the entity circle."""
    if not hasattr(entity, "hp") or not hasattr(entity, "max_hp"):
        return

    bar_w = radius * 2 + 4
    bar_h = 4
    bar_x = sx - radius - 2
    bar_y = sy - radius - 8 - bar_h

    # HP bar: red background, green fill
    hp_ratio = max(0.0, entity.hp / entity.max_hp) if entity.max_hp > 0 else 0.0
    pygame.draw.rect(surface, (180, 0, 0), (bar_x, bar_y, bar_w, bar_h))
    pygame.draw.rect(surface, (0, 200, 0), (bar_x, bar_y, int(bar_w * hp_ratio), bar_h))

    # Cargo bar for MiningShip in MINING state
    if (type(entity).__name__ == "MiningShip"
            and getattr(entity, "state", None) == "MINING"
            and hasattr(entity, "cargo") and hasattr(entity, "cargo_cap")
            and entity.cargo_cap > 0):
        cargo_ratio = max(0.0, entity.cargo / entity.cargo_cap)
        cargo_y = bar_y + bar_h + 1
        pygame.draw.rect(surface, (0, 0, 100), (bar_x, cargo_y, bar_w, bar_h))
        pygame.draw.rect(surface, (0, 120, 255), (bar_x, cargo_y, int(bar_w * cargo_ratio), bar_h))


def _draw_entities(surface, world, fog, cam_x, cam_y, selection):
    for e in world.entities:
        if not should_draw_entity(e, fog):
            continue
        wx = int(e.pos.x - cam_x)
        wy = int(e.pos.y - cam_y)
        if -30 > wx or wx > SCREEN_WIDTH + 30:
            continue
        if -30 > wy or wy > SCREEN_HEIGHT + 30:
            continue
        col = _colour_of(e)
        r   = _radius_of(e)
        pygame.draw.circle(surface, col, (wx, wy), r)
        if e in selection:
            pygame.draw.circle(surface, (255, 255, 0), (wx, wy), r + 3, 2)
        # Hit flash overlay
        if getattr(e, "_hit_flash", 0) > 0:
            flash_surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(flash_surf, (255, 0, 0, 160), (r + 1, r + 1), r)
            surface.blit(flash_surf, (wx - r - 1, wy - r - 1))
        _draw_unit_bars(surface, e, wx, wy, r)


def _draw_hud(surface, world, font):
    # Resource bar
    res = world.resources[TEAM_PLAYER]
    txt = font.render(f"Minerals: {res}", True, (220, 220, 220))
    surface.blit(txt, (10, 10))


def _draw_win_screen(surface, result, font_big):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))
    if result == "player_win":
        msg = "VICTORY!"
        col = (80, 255, 100)
    else:
        msg = "DEFEAT..."
        col = (255, 80, 80)
    txt = font_big.render(msg, True, col)
    surface.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2,
                       SCREEN_HEIGHT // 2 - txt.get_height() // 2 - 20))
    sub = font_big.render("Press R to restart  |  ESC to quit", True, (200, 200, 200))
    surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2,
                       SCREEN_HEIGHT // 2 + 30))


# ── Input helpers ─────────────────────────────────────────────────

def _world_to_screen(wx, wy, cam_x, cam_y):
    return wx - cam_x, wy - cam_y


def _screen_to_world(sx, sy, cam_x, cam_y):
    return sx + cam_x, sy + cam_y


def _entity_at(world, wx, wy, radius=14):
    for e in reversed(world.entities):   # top-most first
        if isinstance(e, Asteroid):
            continue
        dist = e.pos.distance_to((wx, wy))
        if dist <= max(radius, _radius_of(e) + 4):
            return e
    return None


def _entities_in_rect(world, rect_world):
    """rect_world: pygame.Rect in world coordinates."""
    result = []
    for e in world.entities:
        if isinstance(e, Asteroid):
            continue
        if not hasattr(e, "team") or e.team != TEAM_PLAYER:
            continue
        if rect_world.collidepoint(e.pos.x, e.pos.y):
            result.append(e)
    return result


# ── Main loop ─────────────────────────────────────────────────────

def build_test_world() -> World:
    w = World()
    w.resources[TEAM_PLAYER] = 500
    w.resources[TEAM_ENEMY]  = 200   # bootstrap: AI needs minerals to buy its first miner

    # Player mothership
    pm = Mothership(pos=(300, 300), team=TEAM_PLAYER)
    w.add_entity(pm)

    # Player ships
    for i in range(3):
        s = CombatShip(pos=(320 + i * 30, 340), size="S", team=TEAM_PLAYER)
        w.add_entity(s)
    w.add_entity(MiningShip(pos=(280, 360), team=TEAM_PLAYER))
    w.add_entity(BuilderShip(pos=(260, 360), team=TEAM_PLAYER))

    # Enemy mothership
    em = Mothership(pos=(2700, 2700), team=TEAM_ENEMY)
    w.add_entity(em)

    # Enemy ships
    for i in range(2):
        s = CombatShip(pos=(2720 + i * 30, 2720), size="M", team=TEAM_ENEMY)
        w.add_entity(s)

    # Asteroids
    random.seed(42)
    for _ in range(12):
        pos = (random.randint(200, MAP_WIDTH - 200),
               random.randint(200, MAP_HEIGHT - 200))
        size = random.choice(("S", "M", "L"))
        w.add_entity(Asteroid(pos=pos, size=size))

    return w


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Sonor")
    clock = pygame.time.Clock()
    font      = pygame.font.SysFont("monospace", 14)
    font_big  = pygame.font.SysFont("monospace", 36)

    def _new_game():
        w = build_test_world()
        return w, FogMap(MAP_WIDTH, MAP_HEIGHT), SonarFX(), EnemyAI()

    world, fog, sonar_fx, enemy_ai = _new_game()

    # Sonar subsystems
    minimap   = Minimap(map_w=MAP_WIDTH, map_h=MAP_HEIGHT, mm_w=200, mm_h=150)
    _MM_X = SCREEN_WIDTH - 200 - 10   # minimap top-left screen x
    _MM_Y = 10                         # minimap top-left screen y
    passive   = PassiveDetector()
    sonar_hits: list = []   # accumulated contacts this frame

    # Game systems
    mining_sys  = MiningSystem()
    build_sys   = BuildSystem()
    combat_sys  = CombatSystem()

    # Panel surface (bottom 160px strip)
    _PANEL_H = 160
    _PANEL_Y = SCREEN_HEIGHT - _PANEL_H
    panel_surf = pygame.Surface((SCREEN_WIDTH, _PANEL_H), pygame.SRCALPHA)
    control_panel = ControlPanel(panel_y=_PANEL_Y)

    # Unit Roster (left side, from HUD to panel top)
    _ROSTER_Y = 30          # below HUD line
    _ROSTER_H = _PANEL_Y - _ROSTER_Y
    roster = UnitRoster(panel_y_start=_ROSTER_Y, panel_h=_ROSTER_H)

    # Camera (top-left world coordinate)
    cam_x, cam_y = 200.0, 200.0

    # Selection state
    selection: list = []
    drag_start = None   # screen pos where drag began
    drag_rect  = None   # current drag rect (screen coords)

    game_result = None   # "player_win" | "player_lose" | None

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        mx, my = pygame.mouse.get_pos()

        # ── Events ────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r and game_result is not None:
                    # Restart
                    world, fog, sonar_fx, enemy_ai = _new_game()
                    selection = []; game_result = None
                    control_panel.set_selection([], world=world)
                # Sonar toggle for selection
                if event.key == pygame.K_s:
                    for e in selection:
                        if hasattr(e, "sonar"):
                            e.sonar.toggle()
                # Speed boost toggle
                if event.key == pygame.K_b:
                    for e in selection:
                        if hasattr(e, "speed_mode"):
                            e.speed_mode.toggle()

            # Pass events to control panel first
            if control_panel.handle_event(event):
                pass   # consumed

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if control_panel.in_panel(event.pos):
                    pass   # click inside panel area but missed all buttons — ignore

                elif (event.button == 1
                      and pygame.Rect(_MM_X, _MM_Y, minimap.mm_w, minimap.mm_h)
                             .collidepoint(event.pos)):
                    # Minimap click — centre camera on the clicked world position
                    lx = event.pos[0] - _MM_X
                    ly = event.pos[1] - _MM_Y
                    cam_x = lx / minimap.mm_w * MAP_WIDTH  - SCREEN_WIDTH  // 2
                    cam_y = ly / minimap.mm_h * MAP_HEIGHT - SCREEN_HEIGHT // 2
                    cam_x = max(0, min(cam_x, MAP_WIDTH  - SCREEN_WIDTH))
                    cam_y = max(0, min(cam_y, MAP_HEIGHT - SCREEN_HEIGHT))

                elif event.button == 1:   # left click — start selection or roster
                    if roster.in_roster(event.pos):
                        shift_held = pygame.key.get_mods() & pygame.KMOD_SHIFT
                        selection  = roster.handle_click(
                            event.pos, world, selection, bool(shift_held))
                        control_panel.set_selection(selection, world=world)
                        if roster.camera_jump:
                            e = roster.camera_jump
                            roster.camera_jump = None
                            cam_x = e.pos.x - SCREEN_WIDTH  // 2
                            cam_y = e.pos.y - SCREEN_HEIGHT // 2
                            cam_x = max(0, min(cam_x, MAP_WIDTH  - SCREEN_WIDTH))
                            cam_y = max(0, min(cam_y, MAP_HEIGHT - SCREEN_HEIGHT))
                    else:
                        drag_start = event.pos
                        drag_rect  = None

                elif event.button == 3:  # right click — move / command
                    wx, wy = _screen_to_world(mx, my, cam_x, cam_y)
                    target_vec = pygame.Vector2(wx, wy)
                    # Check if right-clicking an asteroid (assign mining ship)
                    clicked_ast = None
                    for e in world.entities:
                        if isinstance(e, Asteroid) and e.pos.distance_to(target_vec) < 30:
                            clicked_ast = e
                            break
                    # Ships that will receive a plain move target get
                    # formation offsets so they don't all stack on one point.
                    _move_sel = [
                        e for e in selection
                        if (isinstance(e, MiningShip) and not clicked_ast)
                        or (not isinstance(e, (MiningShip, BuilderShip))
                            and hasattr(e, "_target_pos"))
                    ]
                    _offsets = formation_offsets(len(_move_sel))
                    _offset_map = {id(e): off for e, off in zip(_move_sel, _offsets)}

                    for e in selection:
                        if isinstance(e, MiningShip):
                            if clicked_ast:
                                e.assigned_asteroid = clicked_ast
                                e.state = "MOVING_TO_AST"
                            else:
                                e.assigned_asteroid = None
                                e._target_pos = target_vec + _offset_map[id(e)]
                                e.state = "IDLE"
                        elif isinstance(e, BuilderShip):
                            e.assigned_target = target_vec
                            # Auto-detect: near asteroid → Station, elsewhere → Turret
                            from constants import STATION_ATTACH_RADIUS
                            near_ast = any(
                                ast.pos.distance_to(target_vec) <= STATION_ATTACH_RADIUS
                                for ast in world.asteroids
                            )
                            e.building_type = "MiningStation" if near_ast else "Turret"
                            e.state = "MOVING_TO_SITE"
                        elif hasattr(e, "_target_pos"):
                            e._target_pos = target_vec + _offset_map.get(
                                id(e), pygame.Vector2(0, 0)
                            )

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and drag_start and not control_panel.in_panel(event.pos):
                    ex, ey = event.pos
                    dx = abs(ex - drag_start[0])
                    dy = abs(ey - drag_start[1])
                    if dx < 5 and dy < 5:
                        # Single click
                        wx, wy = _screen_to_world(mx, my, cam_x, cam_y)
                        hit = _entity_at(world, wx, wy)
                        if hit and hasattr(hit, "team") and hit.team == TEAM_PLAYER:
                            selection = [hit]
                        else:
                            selection = []
                    else:
                        # Box select
                        x0 = min(drag_start[0], ex)
                        y0 = min(drag_start[1], ey)
                        w2 = abs(ex - drag_start[0])
                        h2 = abs(ey - drag_start[1])
                        sr = pygame.Rect(x0, y0, w2, h2)
                        # Convert to world rect
                        wx0, wy0 = _screen_to_world(sr.x, sr.y, cam_x, cam_y)
                        wr = pygame.Rect(wx0, wy0, sr.width, sr.height)
                        selection = _entities_in_rect(world, wr)
                    drag_start = None
                    drag_rect  = None
                    control_panel.set_selection(selection, world=world)

            elif event.type == pygame.MOUSEMOTION:
                if drag_start and drag_start[0] >= UnitRoster.PANEL_W:
                    ex, ey = event.pos
                    x0 = min(drag_start[0], ex)
                    y0 = min(drag_start[1], ey)
                    drag_rect = pygame.Rect(x0, y0,
                                            abs(ex - drag_start[0]),
                                            abs(ey - drag_start[1]))

        # ── Camera movement ───────────────────────────────────────
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] or (mx < CAMERA_EDGE_MARGIN):
            cam_x -= CAMERA_SPEED * dt
        if keys[pygame.K_d] or (mx > SCREEN_WIDTH - CAMERA_EDGE_MARGIN):
            cam_x += CAMERA_SPEED * dt
        if keys[pygame.K_w] or (my < CAMERA_EDGE_MARGIN):
            cam_y -= CAMERA_SPEED * dt
        if keys[pygame.K_DOWN] or (my > SCREEN_HEIGHT - CAMERA_EDGE_MARGIN):
            cam_y += CAMERA_SPEED * dt
        if keys[pygame.K_LEFT]:
            cam_x -= CAMERA_SPEED * dt
        if keys[pygame.K_RIGHT]:
            cam_x += CAMERA_SPEED * dt
        if keys[pygame.K_UP]:
            cam_y -= CAMERA_SPEED * dt

        cam_x = max(0, min(cam_x, MAP_WIDTH  - SCREEN_WIDTH))
        cam_y = max(0, min(cam_y, MAP_HEIGHT - SCREEN_HEIGHT))

        # ── Simple unit movement (CombatShip only) ───────────────
        for e in world.entities:
            if isinstance(e, (MiningShip, BuilderShip)):
                continue   # handled by their respective systems
            if hasattr(e, "_target_pos") and e._target_pos is not None:
                spd = e.speed_mode.effective_speed(e.speed) if hasattr(e, "speed_mode") else e.speed
                direction = e._target_pos - e.pos
                dist = direction.length()
                if dist < spd * dt:
                    e.pos = pygame.Vector2(e._target_pos)
                    e._target_pos = None
                    if hasattr(e, "state"):
                        e.state = "IDLE"
                else:
                    e.pos += direction.normalize() * spd * dt

        # ── Game systems ──────────────────────────────────────────
        if game_result is None:
            mining_sys.update(world, dt)
            build_sys.update(world, dt)
            combat_sys.update(world, dt)
            enemy_ai.update(world, dt)
            resolve_separation(world)

            # ── Mothership build queues ───────────────────────────────
            for e in list(world.entities):
                if not isinstance(e, Mothership):
                    continue
                for q in e.build_queues:
                    result = q.update(dt)
                    if result is None:
                        continue
                    # Spawn the produced unit near the mothership
                    spawn_pos = (e.pos.x + 40, e.pos.y + 40)
                    if result == "CombatShip_S":
                        world.add_entity(CombatShip(pos=spawn_pos, size="S", team=e.team))
                    elif result == "CombatShip_M":
                        world.add_entity(CombatShip(pos=spawn_pos, size="M", team=e.team))
                    elif result == "CombatShip_L":
                        world.add_entity(CombatShip(pos=spawn_pos, size="L", team=e.team))
                    elif result == "MiningShip":
                        world.add_entity(MiningShip(pos=spawn_pos, team=e.team))
                    elif result == "BuilderShip":
                        world.add_entity(BuilderShip(pos=spawn_pos, team=e.team))

            game_result = world.check_win_condition()

        # ── Fog update ────────────────────────────────────────────
        player_units = world.entities_for_team(0)
        fog.update(player_units)
        fog.reveal_asteroids(world.asteroids)

        # ── Sonar update ──────────────────────────────────────────
        sonar_hits = []

        # Active sonar: tick SonarController, fire pulses
        for e in world.entities:
            if not hasattr(e, "sonar"):
                continue
            if e.sonar.update(dt):
                strength = getattr(e, "sonar_strength", 1)
                pulse = ActivePulse(origin=(e.pos.x, e.pos.y), strength=strength)
                sonar_fx.add_pulse(pulse)

        # Check hits against current pulses before advancing them
        all_entities = list(world.entities)
        for pulse in sonar_fx.pulses:
            hits = pulse.check_hit(all_entities)
            for h in hits:
                sonar_fx.add_hit(h)
                sonar_hits.append(h)
        # Advance pulses and expire dead ones
        sonar_fx.update(dt)

        # Passive sonar: detect moving enemies
        enemy_units = world.entities_for_team(1)
        passive_hits = passive.detect(player_units, enemy_units, dt)
        for h in passive_hits:
            sonar_fx.add_hit(h)
            sonar_hits.append(h)

        # Reveal asteroids via sonar hits
        mining_sys.reveal_by_hits(world, sonar_hits)

        # ── Hit flash decay ───────────────────────────────────────
        for e in world.entities:
            if hasattr(e, "_hit_flash"):
                e._hit_flash = max(0.0, e._hit_flash - dt)

        # ── Draw ──────────────────────────────────────────────────
        screen.fill((5, 5, 15))

        # Map border
        border = pygame.Rect(-cam_x, -cam_y, MAP_WIDTH, MAP_HEIGHT)
        pygame.draw.rect(screen, (30, 30, 50), border, 2)

        _draw_entities(screen, world, fog, cam_x, cam_y, selection)

        # Fog overlay (covers unknown areas)
        fog.draw(screen, (cam_x, cam_y))

        # Sonar FX overlay (above fog so hits are visible through darkness)
        sonar_fx.draw(screen, (cam_x, cam_y))

        # Minimap (top-right corner, avoids control panel overlap)
        mm_x = SCREEN_WIDTH - minimap.mm_w - 10
        mm_y = 10
        mm_surf = pygame.Surface((minimap.mm_w, minimap.mm_h), pygame.SRCALPHA)
        minimap.draw(mm_surf, world, sonar_hits)
        # Viewport indicator — white rectangle showing the visible area
        vx = cam_x / MAP_WIDTH  * minimap.mm_w
        vy = cam_y / MAP_HEIGHT * minimap.mm_h
        vw = SCREEN_WIDTH  / MAP_WIDTH  * minimap.mm_w
        vh = SCREEN_HEIGHT / MAP_HEIGHT * minimap.mm_h
        pygame.draw.rect(mm_surf, (255, 255, 255),
                         (int(vx), int(vy), int(vw), int(vh)), 1)
        screen.blit(mm_surf, (mm_x, mm_y))

        if drag_rect and drag_rect.width > 2 and drag_rect.height > 2:
            s = pygame.Surface((drag_rect.width, drag_rect.height), pygame.SRCALPHA)
            s.fill((100, 200, 255, 40))
            screen.blit(s, drag_rect.topleft)
            pygame.draw.rect(screen, (100, 200, 255), drag_rect, 1)

        _draw_hud(screen, world, font)

        # Unit roster (left side panel)
        roster.draw(screen, world, selection)

        # Control panel (bottom strip)
        panel_surf.fill((0, 0, 0, 0))
        control_panel.draw(panel_surf)
        screen.blit(panel_surf, (0, SCREEN_HEIGHT - _PANEL_H))

        # Win/lose overlay
        if game_result is not None:
            _draw_win_screen(screen, game_result, font_big)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
