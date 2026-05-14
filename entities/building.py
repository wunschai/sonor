from entities.unit import Unit
from constants import (
    MOTHERSHIP_HP, MOTHERSHIP_VISION, MOTHERSHIP_QUEUES,
    TURRET_HP, TURRET_DAMAGE, TURRET_FIRE_RATE, TURRET_ATTACK_RANGE,
    STATION_HP, STATION_MINE_RATE, STATION_BUFFER_CAP,
    TEAM_PLAYER,
)


class BuildQueue:
    """Single production queue slot on a mothership."""
    from collections import deque

    def __init__(self):
        from collections import deque
        self.queue = deque()          # list of (unit_type_str, build_time)
        self.progress = 0.0           # seconds elapsed on current item
        self.producing = None         # unit_type_str | None

    def enqueue(self, unit_type: str, build_time: float,
                cost: int, resources: int) -> bool:
        """Add unit_type to queue. Returns False if resources low or queue full."""
        from constants import MOTHERSHIP_QUEUE_SLOTS
        if resources < cost:
            return False
        if len(self.queue) + (1 if self.producing else 0) >= MOTHERSHIP_QUEUE_SLOTS:
            return False
        self.queue.append((unit_type, build_time))
        if self.producing is None:
            self._start_next()
        return True

    def _start_next(self):
        if self.queue:
            self.producing, self._current_build_time = self.queue.popleft()
            self.progress = 0.0
        else:
            self.producing = None
            self._current_build_time = 0.0

    def update(self, dt: float):
        """Advance production. Returns unit_type str when done, else None."""
        if self.producing is None:
            return None
        self.progress += dt
        if self.progress >= self._current_build_time:
            finished = self.producing
            self._start_next()
            return finished
        return None


class Mothership(Unit):
    """Player / enemy flagship — cannot be built, loss condition if destroyed."""

    def __init__(self, *, pos, team):
        super().__init__(
            pos=pos,
            hp=MOTHERSHIP_HP,
            size="L",
            team=team,
            vision_radius=MOTHERSHIP_VISION,
            speed=0.0,
        )
        self.build_queues = [BuildQueue() for _ in range(MOTHERSHIP_QUEUES)]


class MiningStation(Unit):
    """Auto-mines when no mining ship is attached to the same asteroid."""

    def __init__(self, *, pos, team):
        super().__init__(
            pos=pos,
            hp=STATION_HP,
            size="M",
            team=team,
            vision_radius=0.0,
            speed=0.0,
        )
        self.buffer = 0
        self.buffer_cap = STATION_BUFFER_CAP
        self.mine_rate = float(STATION_MINE_RATE)
        self.attached_asteroid = None   # Asteroid | None


class Turret(Unit):
    """Static defensive structure, combat power = medium ship."""

    def __init__(self, *, pos, team):
        super().__init__(
            pos=pos,
            hp=TURRET_HP,
            size="M",
            team=team,
            vision_radius=0.0,
            speed=0.0,
        )
        self.damage = TURRET_DAMAGE
        self.fire_rate = float(TURRET_FIRE_RATE)
        self.attack_range = float(TURRET_ATTACK_RANGE)
        self._fire_timer = 1.0 / TURRET_FIRE_RATE
