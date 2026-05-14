import pygame


class Unit:
    """Base class for all game entities."""

    def __init__(self, *, pos, hp, size, team, vision_radius, speed):
        self.pos = pygame.Vector2(pos)
        self.max_hp = hp
        self.hp = hp
        self.size = size          # "S" | "M" | "L"
        self.team = team          # TEAM_PLAYER | TEAM_ENEMY
        self.vision_radius = float(vision_radius)
        self.speed = float(speed)

    @property
    def alive(self):
        return self.hp > 0

    def take_damage(self, amount: int) -> bool:
        """Reduce HP by amount. Returns True if unit dies."""
        self.hp = max(0, self.hp - amount)
        return self.hp == 0
