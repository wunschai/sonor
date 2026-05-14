import math
import pygame


class Asteroid:
    """Ore source. Infinite ore in prototype."""

    def __init__(self, *, pos, size):
        assert size in ("S", "M", "L"), f"Invalid asteroid size: {size}"
        self.pos = pygame.Vector2(pos)
        self.size = size
        self.ore_amount = math.inf
        self.revealed = False
        self._attached_ships = []   # list of MiningShip currently attached

    def has_attached_ship(self) -> bool:
        return len(self._attached_ships) > 0

    def attach(self, ship):
        if ship not in self._attached_ships:
            self._attached_ships.append(ship)

    def detach(self, ship):
        if ship in self._attached_ships:
            self._attached_ships.remove(ship)
