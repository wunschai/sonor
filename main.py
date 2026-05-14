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
from entities.ship import CombatShip, MiningShip, BuilderShip
from entities.building import Mothership, Turret, MiningStation
from entities.asteroid import Asteroid


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


def _draw_entities(surface, world, cam_x, cam_y, selection):
    for e in world.entities:
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


def _draw_hud(surface, world, selection, font):
    # Resource bar
    res = world.resources[TEAM_PLAYER]
    txt = font.render(f"Minerals: {res}", True, (220, 220, 220))
    surface.blit(txt, (10, 10))

    # Selection info strip
    if selection:
        panel_rect = pygame.Rect(0, SCREEN_HEIGHT - 80, SCREEN_WIDTH, 80)
        pygame.draw.rect(surface, COL_HUD_BG, panel_rect)
        e = selection[0]
        name = type(e).__name__
        info = f"{name}"
        if hasattr(e, "hp"):
            info += f"  HP: {e.hp}/{e.max_hp}"
        if hasattr(e, "size"):
            info += f"  [{e.size}]"
        txt = font.render(info, True, (220, 220, 220))
        surface.blit(txt, (10, SCREEN_HEIGHT - 65))


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
    font  = pygame.font.SysFont("monospace", 14)

    world = build_test_world()

    # Camera (top-left world coordinate)
    cam_x, cam_y = 200.0, 200.0

    # Selection state
    selection: list = []
    drag_start = None   # screen pos where drag began
    drag_rect  = None   # current drag rect (screen coords)

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

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:   # left click — start selection
                    drag_start = event.pos
                    drag_rect  = None

                elif event.button == 3:  # right click — move / command
                    wx, wy = _screen_to_world(mx, my, cam_x, cam_y)
                    for e in selection:
                        if hasattr(e, "_target_pos"):
                            e._target_pos = pygame.Vector2(wx, wy)
                            e.state = "MOVING_TO_SITE" if hasattr(e, "building_type") else "MOVING_TO_AST"

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and drag_start:
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

            elif event.type == pygame.MOUSEMOTION:
                if drag_start:
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
        if keys[pygame.K_s and 0]:   # WASD-only, S is sonar
            pass
        if keys[pygame.K_DOWN] or (my > SCREEN_HEIGHT - CAMERA_EDGE_MARGIN - 80):
            cam_y += CAMERA_SPEED * dt
        if keys[pygame.K_LEFT]:
            cam_x -= CAMERA_SPEED * dt
        if keys[pygame.K_RIGHT]:
            cam_x += CAMERA_SPEED * dt
        if keys[pygame.K_UP]:
            cam_y -= CAMERA_SPEED * dt

        cam_x = max(0, min(cam_x, MAP_WIDTH  - SCREEN_WIDTH))
        cam_y = max(0, min(cam_y, MAP_HEIGHT - SCREEN_HEIGHT))

        # ── Simple unit movement ──────────────────────────────────
        for e in world.entities:
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

        # ── Draw ──────────────────────────────────────────────────
        screen.fill((5, 5, 15))

        # Map border
        border = pygame.Rect(-cam_x, -cam_y, MAP_WIDTH, MAP_HEIGHT)
        pygame.draw.rect(screen, (30, 30, 50), border, 2)

        _draw_entities(screen, world, cam_x, cam_y, selection)

        if drag_rect and drag_rect.width > 2 and drag_rect.height > 2:
            s = pygame.Surface((drag_rect.width, drag_rect.height), pygame.SRCALPHA)
            s.fill((100, 200, 255, 40))
            screen.blit(s, drag_rect.topleft)
            pygame.draw.rect(screen, (100, 200, 255), drag_rect, 1)

        _draw_hud(screen, world, selection, font)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
