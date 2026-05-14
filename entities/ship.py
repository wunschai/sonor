from entities.unit import Unit
from constants import (
    TEAM_PLAYER,
    SHIP_HP, SHIP_SPEED, SHIP_VISION, SHIP_SONAR_STR,
    SHIP_DAMAGE, SHIP_FIRE_RATE, SHIP_ATTACK_RANGE,
    MINING_SHIP_HP, MINING_SHIP_SPEED, MINING_SHIP_VISION,
    BUILDER_SHIP_HP, BUILDER_SHIP_SPEED, BUILDER_SHIP_VISION,
    CARGO_CAP, BOOST_SPEED_MULT, SONAR_INTERVAL,
)


class SonarController:
    """Manages per-ship active sonar toggle and auto-fire timer."""

    def __init__(self, interval: float = SONAR_INTERVAL):
        self.active = False
        self.timer = 0.0
        self.interval = interval

    def toggle(self):
        self.active = not self.active
        if not self.active:
            self.timer = 0.0

    def update(self, dt: float) -> bool:
        """Advance timer. Returns True when a pulse should fire."""
        if not self.active:
            return False
        self.timer += dt
        if self.timer >= self.interval:
            self.timer -= self.interval
            return True
        return False


class SpeedMode:
    """Normal / boost speed toggle for any mobile ship."""

    def __init__(self):
        self.boosting = False

    def toggle(self):
        self.boosting = not self.boosting

    def effective_speed(self, base_speed: float) -> float:
        return base_speed * BOOST_SPEED_MULT if self.boosting else base_speed


class CombatShip(Unit):
    """Warship in S / M / L size."""

    def __init__(self, *, pos, size, team):
        super().__init__(
            pos=pos,
            hp=SHIP_HP[size],
            size=size,
            team=team,
            vision_radius=SHIP_VISION[size],
            speed=SHIP_SPEED[size],
        )
        self.damage = SHIP_DAMAGE[size]
        self.fire_rate = SHIP_FIRE_RATE[size]
        self.attack_range = float(SHIP_ATTACK_RANGE[size])
        self.sonar_strength = SHIP_SONAR_STR[size]
        self.sonar = SonarController()
        self.speed_mode = SpeedMode()
        self._fire_timer = 1.0 / self.fire_rate   # time until next shot


class MiningShip(Unit):
    """Harvests ore from asteroids and returns to mothership."""

    STATES = ("IDLE", "MOVING_TO_AST", "MINING",
              "MOVING_TO_BASE", "COLLECTING_STATION")

    def __init__(self, *, pos, team):
        super().__init__(
            pos=pos,
            hp=MINING_SHIP_HP,
            size="S",
            team=team,
            vision_radius=MINING_SHIP_VISION,
            speed=MINING_SHIP_SPEED,
        )
        self.cargo = 0
        self.cargo_cap = CARGO_CAP
        self.assigned_asteroid = None   # Asteroid | None
        self.state = "IDLE"
        self.sonar = SonarController()
        self.speed_mode = SpeedMode()
        self._target_pos = None         # pygame.Vector2 | None


class BuilderShip(Unit):
    """Constructs buildings at designated map positions."""

    STATES = ("IDLE", "MOVING_TO_SITE", "BUILDING", "WAITING_RESOURCES")

    def __init__(self, *, pos, team):
        super().__init__(
            pos=pos,
            hp=BUILDER_SHIP_HP,
            size="S",
            team=team,
            vision_radius=BUILDER_SHIP_VISION,
            speed=BUILDER_SHIP_SPEED,
        )
        self.assigned_target = None     # pygame.Vector2 | None
        self.building_type = None       # str | None  e.g. "MiningStation"
        self.state = "IDLE"
        self.sonar = SonarController()
        self.speed_mode = SpeedMode()
        self._build_progress = 0.0
        self._building_entity = None    # in-progress Building | None
