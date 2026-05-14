"""ControlPanel — dynamic button strip for the selected unit(s)."""
from __future__ import annotations
import pygame
from dataclasses import dataclass, field
from typing import Callable, List

from entities.ship import CombatShip, MiningShip, BuilderShip
from entities.building import Mothership, Turret, MiningStation
from constants import COL_HUD_BG, COL_PLAYER


# ── Button ────────────────────────────────────────────────────────

@dataclass
class PanelButton:
    name:     str
    label:    str
    rect:     pygame.Rect
    on_click: Callable[[], None]
    active:   Callable[[], bool] = field(default=lambda: False)


# ── ControlPanel ──────────────────────────────────────────────────

_COL_BTN_BG     = (35,  45,  60)
_COL_BTN_ACTIVE = (30, 120, 200)
_COL_BTN_HOVER  = (50,  70,  90)
_COL_BTN_BORDER = (80, 120, 180)
_COL_TEXT       = (210, 215, 220)
_COL_TEXT_ACT   = (255, 255, 255)

_BTN_W = 120
_BTN_H = 44
_BTN_PAD = 10
_BTN_Y   = 10


class ControlPanel:
    """Renders a context-sensitive button strip for the current selection."""

    def __init__(self, panel_y: int = 0):
        self.buttons: List[PanelButton] = []
        self._selection: list = []
        self._world = None
        self._panel_y = panel_y   # screen-y where this panel is blitted
        self._font = pygame.font.SysFont("monospace", 13)
        self._small_font = pygame.font.SysFont("monospace", 11)

    # ── Public interface ──────────────────────────────────────────

    def set_selection(self, units: list, world=None) -> None:
        self._selection = list(units)
        self._world = world
        self.buttons = self._build_buttons()

    def in_panel(self, screen_pos) -> bool:
        """Return True if a screen position falls inside the panel strip."""
        return screen_pos[1] >= self._panel_y

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process a pygame event. Returns True if a button consumed it."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Translate screen coords to panel-local coords
            local_pos = (event.pos[0], event.pos[1] - self._panel_y)
            if local_pos[1] >= 0:   # click is inside the panel strip
                for btn in self.buttons:
                    if btn.rect.collidepoint(local_pos):
                        btn.on_click()
                        return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Render panel onto the given surface (fills the whole surface)."""
        if not self._selection:
            return

        # Panel background
        pygame.draw.rect(surface, COL_HUD_BG, surface.get_rect())

        # Unit name / info line
        unit = self._selection[0]
        name = type(unit).__name__
        info = f"{name}"
        if hasattr(unit, "hp"):
            info += f"  HP: {unit.hp}/{unit.max_hp}"
        if hasattr(unit, "size"):
            info += f"  [{unit.size}]"
        txt = self._font.render(info, True, _COL_TEXT)
        surface.blit(txt, (8, 5))

        # Buttons
        for btn in self.buttons:
            is_active = btn.active()
            bg = _COL_BTN_ACTIVE if is_active else _COL_BTN_BG
            pygame.draw.rect(surface, bg, btn.rect, border_radius=4)
            pygame.draw.rect(surface, _COL_BTN_BORDER, btn.rect, 1, border_radius=4)
            col = _COL_TEXT_ACT if is_active else _COL_TEXT
            lbl = self._font.render(btn.label, True, col)
            lx  = btn.rect.centerx - lbl.get_width() // 2
            ly  = btn.rect.centery - lbl.get_height() // 2
            surface.blit(lbl, (lx, ly))

        # Extra info for mining station
        if isinstance(unit, MiningStation):
            buf_txt = self._small_font.render(
                f"Buffer: {int(unit.buffer)}/{unit.buffer_cap}", True, _COL_TEXT)
            surface.blit(buf_txt, (8, surface.get_height() - 20))

        # Build queue progress for Mothership
        if isinstance(unit, Mothership):
            self._draw_build_queues(surface, unit)

    def _draw_build_queues(self, surface: pygame.Surface, ms: Mothership) -> None:
        """Draw build queue progress bars at the bottom of the panel (always shown)."""
        panel_h = surface.get_height()
        bar_w = 160
        bar_h = 8
        pad = 8
        x = pad
        y = panel_h - bar_h - 20

        for i, q in enumerate(ms.build_queues):
            if q.producing is None:
                # Show idle queue so the player knows both queues exist
                label = self._small_font.render(
                    f"Q{i+1}: ——", True, (120, 120, 130))
                surface.blit(label, (x, y - 1))
            else:
                total = getattr(q, "_current_build_time", 1.0)
                if total <= 0:
                    total = 1.0
                ratio     = min(1.0, q.progress / total)
                remaining = max(0.0, total - q.progress)

                # Background bar
                pygame.draw.rect(surface, (200, 200, 200), (x, y, bar_w, bar_h))
                # Progress fill
                pygame.draw.rect(surface, (100, 160, 220), (x, y, int(bar_w * ratio), bar_h))
                pygame.draw.rect(surface, (150, 150, 160), (x, y, bar_w, bar_h), 1)

                label = self._small_font.render(
                    f"Q{i+1}: {q.producing}  {remaining:.1f}s", True, _COL_TEXT)
                surface.blit(label, (x + bar_w + 6, y - 1))

            y -= bar_h + 14

    # ── Button builders ───────────────────────────────────────────

    def _build_buttons(self) -> List[PanelButton]:
        if not self._selection:
            return []
        unit = self._selection[0]

        if isinstance(unit, Mothership):
            return self._mothership_buttons(unit)
        if isinstance(unit, (CombatShip, MiningShip, BuilderShip)):
            return self._ship_buttons(unit)
        if isinstance(unit, Turret):
            return []   # no interactive buttons
        if isinstance(unit, MiningStation):
            return []   # info-only panel
        return []

    def _ship_buttons(self, ship) -> List[PanelButton]:
        buttons = []
        x = _BTN_PAD

        if hasattr(ship, "sonar"):
            btn = PanelButton(
                name="sonar",
                label="Sonar [S]",
                rect=pygame.Rect(x, _BTN_Y + 20, _BTN_W, _BTN_H),
                on_click=ship.sonar.toggle,
                active=lambda s=ship: s.sonar.active,
            )
            buttons.append(btn)
            x += _BTN_W + _BTN_PAD

        if hasattr(ship, "speed_mode"):
            btn = PanelButton(
                name="speed",
                label="Boost [B]",
                rect=pygame.Rect(x, _BTN_Y + 20, _BTN_W, _BTN_H),
                on_click=ship.speed_mode.toggle,
                active=lambda s=ship: s.speed_mode.boosting,
            )
            buttons.append(btn)
            x += _BTN_W + _BTN_PAD

        return buttons

    def _mothership_buttons(self, ms: Mothership) -> List[PanelButton]:
        """One produce-button per ship type per queue."""
        from constants import (
            SHIP_BUILD_COST, SHIP_BUILD_TIME,
            MINING_SHIP_COST, MINING_SHIP_BUILD_TIME,
            BUILDER_SHIP_COST, BUILDER_SHIP_BUILD_TIME,
        )
        buttons = []
        x = _BTN_PAD

        # Queue selector buttons (S / M / L combat ships + mining + builder)
        produce_items = [
            ("Combat S", "CombatShip_S",  SHIP_BUILD_TIME["S"], SHIP_BUILD_COST["S"]),
            ("Combat M", "CombatShip_M",  SHIP_BUILD_TIME["M"], SHIP_BUILD_COST["M"]),
            ("Combat L", "CombatShip_L",  SHIP_BUILD_TIME["L"], SHIP_BUILD_COST["L"]),
            ("Mining",   "MiningShip",    MINING_SHIP_BUILD_TIME,  MINING_SHIP_COST),
            ("Builder",  "BuilderShip",   BUILDER_SHIP_BUILD_TIME, BUILDER_SHIP_COST),
        ]

        for label, unit_type, build_time, cost in produce_items:
            btn = PanelButton(
                name=f"build_{unit_type}",
                label=f"{label}\n${cost}",
                rect=pygame.Rect(x, _BTN_Y + 20, _BTN_W, _BTN_H),
                on_click=self._make_enqueue(ms, unit_type, build_time, cost, self._world),
                active=lambda: False,
            )
            buttons.append(btn)
            x += _BTN_W + _BTN_PAD

        return buttons

    @staticmethod
    def _make_enqueue(ms: Mothership, unit_type: str, build_time: float, cost: int, world):
        def _enqueue():
            resources = world.resources.get(ms.team, 0) if world else 9999
            for q in ms.build_queues:
                if q.enqueue(unit_type, build_time, cost, resources):
                    if world:
                        world.resources[ms.team] = max(0, resources - cost)
                    break
        return _enqueue
