# ─── Map & Display ───────────────────────────────────────────────
MAP_WIDTH  = 3000
MAP_HEIGHT = 3000
SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
FPS = 60

MINIMAP_SIZE   = 200   # square
MINIMAP_MARGIN = 10    # from screen edge

# ─── Camera ──────────────────────────────────────────────────────
CAMERA_SPEED       = 300   # px/s via WASD
CAMERA_EDGE_MARGIN = 40    # px from edge for mouse scroll

# ─── Unit sizes ──────────────────────────────────────────────────
SIZE_FACTORS = {"S": 1, "M": 2, "L": 3}

# ─── Combat ships (S / M / L) ────────────────────────────────────
SHIP_HP           = {"S": 100,  "M": 300,  "L": 700}
SHIP_DAMAGE       = {"S": 10,   "M": 20,   "L": 40}
SHIP_FIRE_RATE    = {"S": 3.0,  "M": 2.0,  "L": 1.0}   # shots/sec
SHIP_ATTACK_RANGE = {"S": 150,  "M": 200,  "L": 250}    # px
SHIP_SPEED        = {"S": 120,  "M": 80,   "L": 50}     # px/s
SHIP_BUILD_TIME   = {"S": 10,   "M": 30,   "L": 70}     # sec
SHIP_BUILD_COST   = {"S": 100,  "M": 200,  "L": 400}    # minerals
SHIP_VISION       = {"S": 120,  "M": 160,  "L": 200}    # px
SHIP_SONAR_STR    = {"S": 1,    "M": 2,    "L": 3}      # pulse strength

# ─── Special units ───────────────────────────────────────────────
MOTHERSHIP_HP     = 2000
MOTHERSHIP_VISION = 250
MOTHERSHIP_QUEUE_SLOTS = 4   # max per build queue
MOTHERSHIP_QUEUES  = 2       # parallel build queues

MINING_SHIP_HP         = 80
MINING_SHIP_VISION     = 100
MINING_SHIP_SPEED      = 100
MINING_SHIP_COST       = 50
MINING_SHIP_BUILD_TIME = 15   # sec

BUILDER_SHIP_HP         = 80
BUILDER_SHIP_VISION     = 100
BUILDER_SHIP_SPEED      = 90
BUILDER_SHIP_COST       = 75
BUILDER_SHIP_BUILD_TIME = 20  # sec

# ─── Buildings ───────────────────────────────────────────────────
TURRET_HP           = 300
TURRET_DAMAGE       = 20
TURRET_FIRE_RATE    = 2.0
TURRET_ATTACK_RANGE = 200
TURRET_COST         = 200
TURRET_BUILD_TIME   = 30   # sec

STATION_HP              = 300
STATION_COST            = 150
STATION_MINE_RATE       = 5      # minerals/sec
STATION_BUFFER_CAP      = 500
STATION_ATTACH_RADIUS   = 150    # px, must be within to auto-attach
STATION_BUILD_TIME      = 20   # sec
STATION_COLLECT_RADIUS  = 80     # px, mining ship picks up buffer

# ─── Mining ──────────────────────────────────────────────────────
MINE_RATE  = 10    # minerals/sec per mining ship
CARGO_CAP  = 100   # minerals per ship

# ─── Sonar ───────────────────────────────────────────────────────
SONAR_INTERVAL    = 3.0    # sec between auto-pulses
PULSE_SPEED       = 200    # px/s
PULSE_DECAY_DIST  = 400    # px per strength level
SONAR_HIT_FADE    = 1.5    # sec for active hit to fade
PASSIVE_RADIUS    = 300    # px
PASSIVE_NOISE     = 20     # ±px position error
PASSIVE_FADE      = 2.0    # sec for passive hit to fade

# Sonar dot radii on minimap (by intensity level 1/2/3)
SONAR_DOT_RADIUS  = {1: 4, 2: 8, 3: 14}
# Sonar outline width on main view (by intensity level 1/2/3)
SONAR_LINE_WIDTH  = {1: 1, 2: 2, 3: 3}

# Volume thresholds → intensity level
PASSIVE_VOL_L1 = 40    # volume < 40 → level 1
PASSIVE_VOL_L2 = 120   # 40 ≤ vol < 120 → level 2
                        # vol ≥ 120 → level 3

# ─── Speed boost ─────────────────────────────────────────────────
BOOST_SPEED_MULT = 1.8

# ─── AI ──────────────────────────────────────────────────────────
AI_ATTACK_THRESHOLD = 5   # combat ships before attacking

# ─── Colours ─────────────────────────────────────────────────────
COL_BLACK        = (0,   0,   0)
COL_WHITE        = (255, 255, 255)
COL_DARK_OVERLAY = (0,   0,   0,   255)    # DARK fog (opaque)
COL_SHROUD       = (0,   0,   0,   160)    # SHROUD fog (semi-transparent)
COL_PLAYER       = (0,   180, 255)
COL_ENEMY        = (255, 60,  60)
COL_ASTEROID     = (160, 120, 60)
COL_MINERAL_MARK = (60,  200, 80)
COL_SONAR_ACTIVE = (255, 255, 255)
COL_SONAR_PASSIVE= (255, 160, 40)
COL_SONAR_PULSE  = (80,  200, 255)
COL_HUD_BG       = (20,  20,  30)

# ─── Teams ───────────────────────────────────────────────────────
TEAM_PLAYER = 0
TEAM_ENEMY  = 1
