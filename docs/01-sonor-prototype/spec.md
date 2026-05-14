# Sonor — 迷霧太空即時戰略遊戲 Prototype

## 目標

建立一個可遊玩的 Prototype，玩家透過聲納系統在迷霧中感知環境，以採礦累積資源、建造艦隊、擊毀敵方母艦獲勝。

## 非目標

- 網路多人對戰
- 音效與背景音樂
- 儲存 / 讀取遊戲進度
- 劇情或任務系統
- 3D 畫面或物理引擎
- 超過一種敵方 AI 難度

---

## User Story 1 — 迷霧戰爭

**作為玩家，我想要只能看見自己單位周圍的區域，以便感受到探索未知宇宙的緊張感。**

### 驗收條件
- [ ] 遊戲開始時全圖為 DARK（純黑）
- [ ] 每個玩家單位以自身為中心，`vision_radius` 範圍內為 VISIBLE（完全透明）
- [ ] 單位移開後，該區域轉為 SHROUD（半透明黑，能看見靜態地形，不顯示動態單位）
- [ ] DARK 區域完全不顯示任何資訊（包含小行星、敵方單位）
- [ ] 每 frame 根據所有玩家單位當前位置重新計算迷霧
- [ ] 已在 SHROUD/VISIBLE 的礦場位置永久顯示標記（不隨迷霧遮蔽）

---

## User Story 2 — 主動聲納

**作為玩家，我想要開關艦艇的主動聲納，讓它定期自動發射脈衝，以便持續掃描黑暗區域。**

### 驗收條件
- [ ] 選取艦艇後按 `S` 鍵，切換該艦艇主動聲納開 / 關（toggle）；HUD 顯示目前狀態
- [ ] 聲納開啟的艦艇每隔 `SONAR_INTERVAL = 3.0 s` 自動發射一圈向外擴散的脈衝環
- [ ] 切換關閉後立即停止計時，不再發射；已在空中的脈衝繼續擴散直至消亡
- [ ] 脈衝環以 `PULSE_SPEED = 200 px/s` 向外擴散
- [ ] 脈衝初始強度 = 艦艇尺寸等級（S=1, M=2, L=3）
- [ ] 每擴散 `PULSE_DECAY_DIST = 400 px`，強度衰減 1 級；降至 0 後脈衝消失
- [ ] 脈衝環觸碰到物件（敵艦、小行星、建物）時：
  - 主視圖：在接觸點顯示輪廓閃光，大小 = `min(物體尺寸, 當前脈衝強度)`（見光點規格）
  - 輪廓閃光從清晰線條在 `SONAR_HIT_FADE = 1.5 s` 內逐漸模糊後消失
  - 小地圖：在對應位置顯示亮白光點，同步 fade out
- [ ] 多艘艦艇可同時有各自的脈衝環，互不干擾

---

## User Story 3 — 被動聲納

**作為玩家，我想要自動偵測附近的移動物體，以便在沒有主動掃描的情況下察覺敵情。**

### 驗收條件
- [ ] 所有玩家單位持續偵測 `PASSIVE_RADIUS = 300 px` 內的移動物件
- [ ] 音量計算：`volume = speed_px_s × SIZE_FACTOR[size]`（SIZE_FACTOR: S=1, M=2, L=3）
- [ ] 音量映射至強度：`< 40` → 1 級；`40–120` → 2 級；`> 120` → 3 級
- [ ] 偵測到後，**僅在小地圖**顯示模糊橘色光點
- [ ] 光點位置加入 `±PASSIVE_NOISE = 20 px` 隨機誤差（每次更新重新取樣）
- [ ] 光點在 `PASSIVE_FADE = 2.0 s` 內模糊消退（若物體持續移動則持續刷新計時）
- [ ] 靜止物體（速度 = 0）不觸發被動聲納

---

## User Story 4 — 採礦

**作為玩家，我想要派採礦船採礦並送回資源、並用採礦站持續供礦，以便建造艦隊。**

### 驗收條件

**採礦船流程：**
- [ ] 地圖上隨機分布小行星（S/M/L 三種），礦物量在 Prototype 設為無限（顯示「∞」）
- [ ] 右鍵點擊小行星，選取中的採礦船前往並自動 attach
- [ ] 採礦船 attach 後每秒採集 `MINE_RATE = 10` 礦物，存入船上的 cargo（上限 `CARGO_CAP = 100`）
- [ ] cargo 滿後採礦船自動返回**母艦**卸貨（不前往採礦站），卸貨後自動返回繼續採礦
- [ ] 卸貨時，若途經採礦站 `STATION_COLLECT_RADIUS = 80 px` 範圍內，採礦船順道取走站內已儲存的礦物（不超過 cargo 剩餘容量），但**卸貨終點仍是母艦**
- [ ] 礦物進入母艦後加入玩家資源池（全局計數器）
- [ ] 小行星被視野或聲納觸及後，在地圖上永久標示（主視圖顯示「∞」標籤，小地圖綠色方塊）

**採礦站：**
- [ ] 採礦站建於小行星旁（施工完成後自動 attach 到最近的小行星，距離需 ≤ `STATION_ATTACH_RADIUS = 150 px`）
- [ ] 採礦站在**無採礦船 attach 同一小行星**時自動採礦，速率 `STATION_MINE_RATE = 5` 礦物/秒，儲存於本地 buffer（上限 `STATION_BUFFER_CAP = 500`）
- [ ] 若有採礦船已 attach 同一小行星，採礦站停止自動採礦（避免搶礦衝突），buffer 保留
- [ ] 採礦船進入 `STATION_COLLECT_RADIUS` 時取走 buffer 中的礦物（如上）
- [ ] 採礦站 buffer 在 HUD / 主視圖標示中顯示當前儲量

---

## User Story 5 — 建造

**作為玩家，我想要花費礦物資源建造艦艇與建物，以便擴充戰力。**

### 驗收條件
- [ ] 母艦有 **2 個獨立平行建造序列**，各自有獨立進度條與佇列
- [ ] 選取母艦後可點擊建造按鈕，選擇要加入哪條序列（預設塞入最短的那條）；扣除資源，若資源不足則拒絕並提示
- [ ] 每條序列依序生產，一艘完成後才開始下一艘；兩條序列互相獨立、同時運作
- [ ] 建造船（Builder）由母艦序列生產；選取建造船後右鍵指定位置 → 選擇建物種類 → 建造船前往施工
- [ ] 建物施工中以進度條顯示，施工中建物有血量，被打爛進度歸零、資源**不退還**
- [ ] 建造完成後建物立即生效（採礦站開始採礦、砲塔開始自動攻擊）
- [ ] 母艦不可由玩家建造，只有初始一艘

---

## User Story 5b — 單位控制面板

**作為玩家，我想要選取單位後看到簡易的操作面板，以便用點擊方式開關功能或下達指令。**

### 驗收條件

**通用（所有可選取單位）：**
- [ ] 選取任意玩家單位後，畫面下方顯示單位控制面板
- [ ] 面板固定顯示：單位名稱、HP 條（當前 / 最大）、尺寸等級（S/M/L）
- [ ] 框選多單位時，顯示所有選取單位的縮圖列表；點擊縮圖可單獨切換選取

**戰鬥艦艇（S / M / L）：**
- [ ] **聲納開關**：Toggle 按鈕顯示「聲納：開 / 關」（點擊切換，快捷鍵 `S` 並存）；開啟時按鈕高亮
- [ ] **速度模式**：Toggle 按鈕顯示「普通 / 加速」（點擊切換，快捷鍵 `B` 並存）；加速模式時移動速度 × `BOOST_SPEED_MULT = 1.8`，被動聲納音量計算改用加速後的速度

**採礦船：**
- [ ] **聲納開關**（同上，採礦船也有聲納）
- [ ] **速度模式**（同上）
- [ ] **指派礦場**：顯示目前 attach 的小行星名稱（或「未指派」）；點擊後進入「等待右鍵點擊小行星」狀態

**建造船：**
- [ ] **聲納開關**
- [ ] **速度模式**
- [ ] **建造選單**：點擊後展開可建造的建物列表（採礦站 / 砲塔），顯示費用；選擇後進入「等待右鍵點擊施工位置」狀態

**母艦：**
- [ ] 顯示 2 條建造序列，各自有進度條與當前生產單位名稱（或「空閒」）
- [ ] 每條序列旁有「加入序列」按鈕，點擊後展開可生產的艦艇列表（採礦船 / 建造船 / S戰艦 / M戰艦 / L戰艦）；列表顯示建造時間與礦物費用
- [ ] 點擊艦艇圖示後加入該序列佇列（資源不足則提示並拒絕）
- [ ] 序列佇列顯示已排隊的單位縮圖（最多顯示 4 格）

**砲塔 / 採礦站（建物）：**
- [ ] 砲塔：顯示攻擊範圍圓（選取時在主視圖繪製半透明圓）
- [ ] 採礦站：顯示當前 buffer 儲量 / 上限（例如「礦物：230 / 500」）

---

## User Story 6 — 戰鬥

**作為玩家，我想要操控艦艇攻擊敵人，以便擊毀敵方母艦獲勝。**

### 驗收條件
- [ ] 艦艇進入 `attack_range` 後自動瞄準並開火（攻擊最近的敵人）
- [ ] 攻擊造成 `damage` 傷害，扣除目標 HP；HP ≤ 0 → 單位消除
- [ ] 敵方母艦 HP ≤ 0 → 玩家勝利畫面
- [ ] 玩家母艦 HP ≤ 0 → 玩家失敗畫面
- [ ] 砲塔自動攻擊射程內的敵人，不可移動
- [ ] 選取單位後下方 HUD 顯示 HP 條（當前/最大）

---

## User Story 7 — 敵方 AI

**作為玩家，我想要有電腦對手可以對戰，以便測試遊戲的可玩性。**

### 驗收條件
- [ ] AI 從地圖另一側的母艦出發，依序執行：採礦 → 建造砲塔 → 建造戰艦 → 進攻
- [ ] AI 在 Prototype 階段可見全圖（不受迷霧限制）
- [ ] AI 達到 `AI_ATTACK_THRESHOLD = 3` 艘戰艦後開始攻擊玩家母艦
- [ ] AI 攻擊時派出所有戰艦組成艦隊前進

---

## 數值規格

### 地圖
| 參數 | 數值 |
|------|------|
| 地圖大小 | 3000 × 3000 px |
| 視窗大小 | 1280 × 720 px |
| 小地圖大小 | 200 × 200 px（右下角） |

### 艦艇基礎數值

| 屬性 | 小 (S) | 中 (M) | 大 (L) |
|------|-------|-------|-------|
| HP | 100 | 300 | 700 |
| 攻擊力 (damage/shot) | 10 | 20 | 40 |
| 攻擊速度 (shots/sec) | 3.0 | 2.0 | 1.0 |
| 攻擊範圍 (px) | 150 | 200 | 250 |
| 移動速度 (px/s) | 120 | 80 | 50 |
| 建造時間 (sec) | 10 | 30 | 70 |
| 建造費用 (礦物) | 100 | 200 | 400 |
| 視野半徑 (px) | 120 | 160 | 200 |
| 聲納發射強度 | 1 | 2 | 3 |

### 特殊單位數值

| 單位 | HP | 視野 (px) | 移動速度 (px/s) | 建造費用 |
|------|-----|--------|------------|------|
| 母艦 | 2000 | 250 | 0（固定） | — |
| 採礦船 | 80 | 100 | 100 | 50 |
| 建造船 | 80 | 100 | 90 | 75 |

### 建物數值

| 建物 | HP | 攻擊力 | 攻擊速度 | 攻擊範圍 | 建造費用 |
|------|-----|------|--------|--------|------|
| 採礦站 | 300 | — | — | — | 150（buffer 上限 500，自動採礦 5/s） |
| 砲塔 | 300 | 20 | 2.0/s | 200 px | 200 |

### 聲納數值

| 參數 | 數值 |
|------|------|
| `BOOST_SPEED_MULT` | 1.8×（加速模式移動速度倍率） |
| `SONAR_INTERVAL` | 3.0 s（開啟聲納的船自動發射間隔） |
| `PULSE_SPEED` | 200 px/s |
| `PULSE_DECAY_DIST` | 400 px（每 400px 衰減 1 級） |
| `SONAR_HIT_FADE` | 1.5 s |
| `PASSIVE_RADIUS` | 300 px |
| `PASSIVE_NOISE` | ±20 px |
| `PASSIVE_FADE` | 2.0 s |

### 聲納光點大小

| 強度等級 | 主視圖輪廓 | 小地圖光點半徑 |
|--------|----------|------------|
| 1 | 細線（1px） | 4 px |
| 2 | 中線（2px） | 8 px |
| 3 | 粗線（3px） | 14 px |

### 音量映射（被動聲納）

```
SIZE_FACTOR: S=1, M=2, L=3
volume = speed_px_s × SIZE_FACTOR

volume < 40       → 強度 1
40 ≤ volume < 120 → 強度 2
volume ≥ 120      → 強度 3
```

---

## 相關檔案

```
sonor/
├── main.py                   # GameLoop，事件分發，60 FPS
├── core/
│   ├── world.py              # World：地圖尺寸、entity 列表、空間索引（grid）
│   ├── fog.py                # FogMap：numpy array 存三態，draw_fog()
│   └── sonar.py              # ActivePulse, PassiveDetector
├── entities/
│   ├── unit.py               # Unit 基類：pos, hp, vision_radius, size
│   ├── ship.py               # Ship(Unit)：combat、mining、builder 子類
│   ├── building.py           # Building(Unit)：Mothership, MiningStation, Turret
│   └── asteroid.py           # Asteroid：revealed flag
├── systems/
│   ├── combat.py             # CombatSystem.update(entities, dt)
│   ├── mining.py             # MiningSystem.update(ships, dt)
│   └── build.py              # BuildSystem：佇列、進度
├── ai/
│   └── enemy.py              # EnemyAI：state machine，update(world, dt)
└── ui/
    ├── minimap.py            # Minimap.draw(surface, world, sonar_hits)
    ├── hud.py                # HUD.draw(surface, selection, resources)
    ├── control_panel.py      # ControlPanel：根據選取單位動態渲染按鈕面板
    └── sonar_fx.py           # SonarFX：pulse ring、hit flash 管理
```

---

## 模組介面 (Key Interfaces)

### `FogMap`
```python
class FogMap:
    DARK    = 0
    SHROUD  = 1
    VISIBLE = 2

    def update(self, player_units: list[Unit]) -> None:
        """每 frame 根據所有玩家單位位置更新迷霧狀態。"""

    def is_visible(self, pos: tuple[float, float]) -> bool:
        """查詢某座標是否當前可見（VISIBLE）。"""

    def draw(self, surface: pygame.Surface, camera_offset: tuple) -> None:
        """將迷霧疊加繪製到 surface 上。"""
```

### `ActivePulse`
```python
@dataclass
class ActivePulse:
    origin: tuple[float, float]
    radius: float          # 當前擴散半徑（px）
    strength: int          # 剩餘強度 1-3
    initial_strength: int  # 發射時的強度

    def update(self, dt: float) -> bool:
        """擴散並衰減；返回 False 表示脈衝已消亡。"""

    def check_hit(self, entities: list[Entity]) -> list[SonarHit]:
        """檢查本 frame 波環是否觸碰到 entity，返回命中清單。"""
```

### `SonarController`（掛在每艘可發射聲納的艦艇上）
```python
class SonarController:
    active: bool = False       # 聲納開關
    timer: float = 0.0         # 距下次發射的倒數計時（秒）
    interval: float = 3.0      # SONAR_INTERVAL

    def toggle(self) -> None:
        """切換 active；關閉時 timer 重置。"""

    def update(self, dt: float) -> bool:
        """倒數計時；返回 True 表示本 frame 應發射脈衝。"""
```

### `SpeedMode`（掛在所有可移動艦艇上）
```python
class SpeedMode:
    boosting: bool = False      # False=普通, True=加速

    def toggle(self) -> None:
        """切換 boosting。"""

    @property
    def effective_speed(self, base_speed: float) -> float:
        """返回當前有效速度（加速時 × BOOST_SPEED_MULT）。"""
```

### `ControlPanel`（UI 層，每 frame 根據 selection 重新渲染）
```python
class ControlPanel:
    selection: list[Unit]       # 當前選取的單位列表

    def set_selection(self, units: list[Unit]) -> None:
        """更新選取；重新建立對應的按鈕組。"""

    def draw(self, surface: pygame.Surface) -> None:
        """繪製面板到畫面下方區域。"""

    def handle_event(self, event: pygame.Event) -> None:
        """處理滑鼠點擊，分發至對應的 toggle / command。"""
```

### `BuildQueue`（母艦持有 2 個實例）
```python
class BuildQueue:
    queue: deque[UnitType]     # 排隊中的生產項目（上限 4）
    progress: float            # 當前生產進度（秒）
    producing: UnitType | None # 當前正在生產的單位類型

    def enqueue(self, unit_type: UnitType, cost: int, resources: int) -> bool:
        """加入佇列；資源不足或佇列滿時返回 False。"""

    def update(self, dt: float) -> Unit | None:
        """推進進度；完成時返回新生成的 Unit 實例，否則返回 None。"""
```

### `SonarHit`
```python
@dataclass
class SonarHit:
    world_pos: tuple[float, float]
    intensity: int    # 1-3
    age: float        # 秒，用於計算 fade
    source: str       # "active" | "passive"
```

### `Unit`（基類）
```python
class Unit:
    pos: pygame.Vector2
    hp: int
    max_hp: int
    size: str           # "S" | "M" | "L"
    vision_radius: float
    team: int           # 0=player, 1=enemy
    speed: float        # px/s

    def take_damage(self, amount: int) -> bool:
        """扣 HP，返回 True 表示單位已死亡。"""
```

### `CombatSystem`
```python
class CombatSystem:
    def update(self, entities: list[Unit], dt: float) -> list[Unit]:
        """處理所有自動攻擊，返回本 frame 死亡的 entity 清單。"""
```

### `EnemyAI`
```python
class EnemyAI:
    state: str  # "idle" | "mining" | "building" | "attacking"

    def update(self, world: World, dt: float) -> None:
        """根據當前狀態執行 AI 決策。"""
```

---

## 邊界案例

| 案例 | 處理方式 |
|------|---------|
| 主動聲納脈衝同時觸碰多個 entity | 每個 entity 各自生成獨立的 `SonarHit`，同 frame 全部處理 |
| 採礦船返回途中母艦被摧毀 | 採礦船進入 IDLE 狀態，停在原位（遊戲通常已結束） |
| 建造中建物被打爛（HP = 0） | 移除建物 entity，佇列跳下一項，資源不退還 |
| 玩家資源不足時點擊建造 | 拒絕加入佇列，HUD 顯示「資源不足」提示文字 1.5 秒 |
| 多艘採礦船同時 attach 同一小行星 | 允許（無限礦物模式），各自獨立計算採礦速率 |
| 脈衝強度衰減至 0 後仍有物體在波環路徑上 | 不觸發命中（強度 0 的脈衝消失，不再偵測） |
| 被動聲納偵測到己方移動單位 | 只偵測**敵方**單位，己方忽略 |
| 靜止的敵方單位（speed = 0） | 不觸發被動聲納（speed = 0 → volume = 0 → 不偵測） |
| 採礦站建造時最近小行星超出 `STATION_ATTACH_RADIUS` | 建物正常完工，但不 attach 任何小行星；HUD 顯示「無小行星可連結」警告，採礦站保持空置（可被攻擊，不採礦） |
| 採礦站 buffer 已滿（500）但仍在自動採礦 | 停止採礦直到 buffer 有空間（被採礦船取走後繼續） |
| 採礦船前往母艦途中路過採礦站，但 cargo 已滿 | 不取走 buffer（cargo 無空間），直接繼續返回母艦 |
| 母艦 2 條序列佇列皆無空位時點擊建造 | 拒絕加入，HUD 提示「建造序列已滿」 |
| 聲納開啟的艦艇被擊沉 | `SonarController` 隨艦艇消除，已在空中的脈衝繼續運行直至消亡 |
| 框選多單位時按 `S` / `B` 快捷鍵 | 對所有選取中的艦艇統一 toggle（開 → 全開，若狀態不一則全部設為「開」） |
| 加速模式下被被動聲納偵測 | 音量計算改用 `effective_speed`（加速後），強度可能升級 |
| 建造船選了建物種類但目標位置資源不足 | 等到資源足夠時才扣除並開始施工（建造船原地等待），玩家可取消 |
| 控制面板按鈕被點擊時單位已不在選取中 | 忽略（selection 已更新，面板重繪後按鈕已消失） |

---

## ADR（Architecture Decision Record）

### ADR-1：迷霧用 numpy array 而非逐像素操作

**決策：** 用 `numpy.ndarray`（shape: `[map_h, map_w]`，dtype `uint8`）存三態，`pygame.surfarray` 快速映射到 Surface。

**原因：** 地圖 3000×3000 = 9M 格，Python 迴圈逐像素操作約需 100ms/frame，無法達到 60 FPS。numpy 向量化操作可降至 2–5ms。

**替代方案：** 用格子（tile）系統降解析度至 32px/格（94×94 格），計算量小但邊緣鋸齒感強，降低視覺質感，捨棄。

---

### ADR-2：ECS 概念但不引入完整 ECS 框架

**決策：** 用 Python 類別模擬 Component 掛載風格，不引入 esper、ecspy 等框架。

**原因：** Prototype 規模的 entity 數量（預估 < 200），完整 ECS 框架的 overhead 帶來的收益不明顯，且增加學習與 debug 成本。Module 邊界清楚已足夠。

**替代方案：** 引入 `esper` 框架——過度設計，排除。

---

### ADR-3：Prototype 階段 AI 作弊可見全圖

**決策：** AI 的 `update()` 直接接收 `World` 物件，可存取全部 entity 位置。

**原因：** 實作 AI 的聲納/迷霧感知需額外設計 AI 的「已知狀態」資料結構，超出 Prototype 目標範圍。

**替代方案：** 讓 AI 也受迷霧限制——功能完整但增加約 30% 複雜度，留待 v2 實作。

---

### ADR-7：控制面板動態渲染，不用繼承樹

**決策：** `ControlPanel` 根據 `selection` 的單位類型，每次 `set_selection()` 時重新建立按鈕列表，而非為每種單位建立 Panel 子類別。

**原因：** 單位種類不多（6–7 種），繼承樹增加檔案數量與跳轉成本；動態組裝按鈕（資料驅動）在這個規模更好 debug 且好擴充新按鈕。

**替代方案：** 每種單位對應一個 `XXXPanel` 子類別——過早的抽象，排除。

---

### ADR-8：加速模式只影響速度與音量，不影響攻擊

**決策：** `BOOST` 僅改變 `effective_speed`，武器 `fire_rate` 與 `damage` 不變。

**原因：** 保持系統簡單：加速的代價是被動聲納暴露（音量升），收益是機動性；若同時影響攻擊力則策略計算複雜度跳升，超出 Prototype 設計目標。

**替代方案：** 加速時攻擊速度也提升——留待後續版本作為艦艇升級選項。

---

### ADR-5：採礦站只在無採礦船時自動採礦

**決策：** 同一小行星有採礦船 attach 時，採礦站停止自動採礦。

**原因：** 避免雙重採礦速率造成礦物產出過高，且「船來了站就休息」符合直覺——站的角色是填補船不在時的空窗，而非與船疊加。

**替代方案：** 採礦站與採礦船各自獨立採礦（速率疊加）——容易讓玩家感覺系統不直觀，排除。

---

### ADR-6：母艦預設 2 條平行建造序列

**決策：** 母艦有 2 個獨立佇列同時運作，各自排隊、各自生產。

**原因：** 單一序列在早期擴張時瓶頸明顯（採礦船/戰艦排隊等待），2 條序列允許玩家同時培養不同兵種（例如一條出採礦船、一條出戰艦），策略空間更豐富，且實作成本不高（兩份相同的佇列物件）。

**替代方案：** 單一佇列——策略層次過薄，排除。3 條或更多——Prototype 過度複雜，留待後續版本。

---

### ADR-4：礦物量設為無限

**決策：** `Asteroid.ore_amount = math.inf`，採礦不扣量。

**原因：** Prototype 重點在驗證聲納 + 戰鬥機制，資源枯竭帶來的策略層次不在本輪測試範圍。

**替代方案：** 有限礦物——留待後續版本加入資源管理深度。
