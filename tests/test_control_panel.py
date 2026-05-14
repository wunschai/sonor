"""Tests for ui/control_panel.py — ControlPanel button generation and dispatch."""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame
pygame.init()

from entities.ship import CombatShip, MiningShip, BuilderShip
from entities.building import Mothership, Turret, MiningStation
from entities.asteroid import Asteroid
from ui.control_panel import ControlPanel
from constants import TEAM_PLAYER, TEAM_ENEMY


# ── Helpers ───────────────────────────────────────────────────────

def _surface(w=1280, h=160):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _combat(size="S"):
    return CombatShip(pos=(0, 0), size=size, team=TEAM_PLAYER)


def _mining():
    return MiningShip(pos=(0, 0), team=TEAM_PLAYER)


def _builder():
    return BuilderShip(pos=(0, 0), team=TEAM_PLAYER)


def _mothership():
    return Mothership(pos=(0, 0), team=TEAM_PLAYER)


def _turret():
    return Turret(pos=(0, 0), team=TEAM_PLAYER)


def _station():
    return MiningStation(pos=(0, 0), team=TEAM_PLAYER)


# ── Button generation ─────────────────────────────────────────────

class TestControlPanelButtonGeneration:
    def test_no_selection_yields_no_buttons(self):
        cp = ControlPanel()
        cp.set_selection([])
        assert cp.buttons == []

    def test_combat_ship_has_sonar_button(self):
        cp = ControlPanel()
        cp.set_selection([_combat()])
        names = [b.name for b in cp.buttons]
        assert "sonar" in names

    def test_combat_ship_has_speed_button(self):
        cp = ControlPanel()
        cp.set_selection([_combat()])
        names = [b.name for b in cp.buttons]
        assert "speed" in names

    def test_mining_ship_has_sonar_and_speed(self):
        cp = ControlPanel()
        cp.set_selection([_mining()])
        names = [b.name for b in cp.buttons]
        assert "sonar" in names
        assert "speed" in names

    def test_builder_ship_has_sonar_and_speed(self):
        cp = ControlPanel()
        cp.set_selection([_builder()])
        names = [b.name for b in cp.buttons]
        assert "sonar" in names
        assert "speed" in names

    def test_mothership_has_build_queue_buttons(self):
        cp = ControlPanel()
        cp.set_selection([_mothership()])
        names = [b.name for b in cp.buttons]
        # Should have buttons to produce units
        assert any("build" in n or "queue" in n or "produce" in n for n in names)

    def test_turret_has_no_interactive_buttons(self):
        cp = ControlPanel()
        cp.set_selection([_turret()])
        # Turrets have no toggle buttons
        names = [b.name for b in cp.buttons]
        assert "sonar" not in names
        assert "speed" not in names

    def test_set_selection_clears_previous(self):
        cp = ControlPanel()
        cp.set_selection([_combat()])
        cp.set_selection([])
        assert cp.buttons == []

    def test_mixed_selection_uses_first_unit(self):
        """When multiple units selected, panel shows first unit's buttons."""
        cp = ControlPanel()
        cp.set_selection([_combat(), _mining()])
        names = [b.name for b in cp.buttons]
        assert "sonar" in names   # both have sonar


# ── Event dispatch ────────────────────────────────────────────────

class TestControlPanelDispatch:
    def test_sonar_button_toggles_sonar(self):
        cp = ControlPanel()
        ship = _combat()
        cp.set_selection([ship])
        assert ship.sonar.active is False
        # Find sonar button and click it
        sonar_btn = next(b for b in cp.buttons if b.name == "sonar")
        sonar_btn.on_click()
        assert ship.sonar.active is True

    def test_speed_button_toggles_speed_mode(self):
        cp = ControlPanel()
        ship = _combat()
        cp.set_selection([ship])
        assert ship.speed_mode.boosting is False
        speed_btn = next(b for b in cp.buttons if b.name == "speed")
        speed_btn.on_click()
        assert ship.speed_mode.boosting is True

    def test_sonar_button_toggle_off(self):
        cp = ControlPanel()
        ship = _combat()
        ship.sonar.toggle()   # on
        cp.set_selection([ship])
        sonar_btn = next(b for b in cp.buttons if b.name == "sonar")
        sonar_btn.on_click()
        assert ship.sonar.active is False

    def test_handle_event_clicks_button(self):
        """handle_event with a MOUSEBUTTONDOWN on a button triggers it."""
        cp = ControlPanel()
        ship = _combat()
        cp.set_selection([ship])
        # Position panel at bottom of an 800×160 surface
        panel_rect = pygame.Rect(0, 0, 1280, 160)
        sonar_btn = next(b for b in cp.buttons if b.name == "sonar")
        # Simulate click at button center
        cx, cy = sonar_btn.rect.centerx, sonar_btn.rect.centery
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (cx, cy)})
        cp.handle_event(event)
        assert ship.sonar.active is True


# ── Drawing ───────────────────────────────────────────────────────

class TestControlPanelDraw:
    def test_draw_does_not_raise_empty(self):
        cp = ControlPanel()
        cp.set_selection([])
        surf = _surface()
        cp.draw(surf)

    def test_draw_does_not_raise_with_combat_ship(self):
        cp = ControlPanel()
        cp.set_selection([_combat()])
        surf = _surface()
        cp.draw(surf)

    def test_draw_does_not_raise_with_mothership(self):
        cp = ControlPanel()
        cp.set_selection([_mothership()])
        surf = _surface()
        cp.draw(surf)

    def test_draw_does_not_raise_with_turret(self):
        cp = ControlPanel()
        cp.set_selection([_turret()])
        surf = _surface()
        cp.draw(surf)

    def test_draw_does_not_raise_with_mining_station(self):
        cp = ControlPanel()
        cp.set_selection([_station()])
        surf = _surface()
        cp.draw(surf)
