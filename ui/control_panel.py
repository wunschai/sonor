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

    def __init__(self):
        self.buttons: List[PanelButton] = []
        self._selection: list = []
        self._font = pygame.font.SysFont("monospace", 13)
        self._small_font = pygame.font.SysFont("monospace", 11)

    # ── Public interface ──────────────────────────────────────────

    def set_selection(self, units: list) -> None:
        self._selection = list(units)
        self.buttons = self._build_buttons()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process a pygame event. Returns True if a button consumed it."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn.rect.collidepoint(event.pos):
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
        from constants import SHIP_BUILD_COST, SHIP_BUILD_TIME, MINING_SHIP_COST, BUILDER_SHIP_COST
        buttons = []
        x = _BTN_PAD

        # Queue selector buttons (simple: S / M / L combat ships + mining + builder)
        produce_items = [
            ("Combat S", "CombatShip_S", SHIP_BUILD_TIME["S"], SHIP_BUILD_COST["S"]),
            ("Combat M", "CombatShip_M", SHIP_BUILD_TIME["M"], SHIP_BUILD_COST["M"]),
            ("Combat L", "CombatShip_L", SHIP_BUILD_TIME["L"], SHIP_BUILD_COST["L"]),
        ]

        for label, unit_type, build_time, cost in produce_items:
            resources = 9999   # placeholder — real wiring in main.py via world
            btn = PanelButton(
                name=f"build_{unit_type}",
                label=f"{label}\n${cost}",
                rect=pygame.Rect(x, _BTN_Y + 20, _BTN_W, _BTN_H),
                on_click=self._make_enqueue(ms, unit_type, build_time, cost),
                active=lambda: False,
            )
            buttons.append(btn)
            x += _BTN_W + _BTN_PAD

        return buttons

    @staticmethod
    def _make_enqueue(ms: Mothership, unit_type: str, build_time: float, cost: int):
        def _enqueue():
            for q in ms.build_queues:
                if q.enqueue(unit_type, build_time, cost, resources=9999):
                    break
        return _enqueue
