# Tasks: Sonor — 迷霧太空即時戰略遊戲 Prototype

---

## Milestone 1: 地基——遊戲框架、實體定義、主迴圈（序列）

> **預期結果：** 可啟動 1280×720 視窗，母艦與數艘測試艦艇以彩色圓形顯示在 3000×3000 地圖上，相機可用 WASD 移動，左鍵選取單位，右鍵可發出移動指令。
> **驗證方式：** `pytest tests/test_entities.py tests/test_world.py` 全過；手動啟動 `main.py` 可見正常視窗

- [x] Task 1.1: 建立專案目錄結構、`requirements.txt`（pygame, numpy, pytest）、`pytest.ini`、`constants.py`（所有數值常數：地圖大小、單位數值、聲納參數）
- [x] Task 1.2: 撰寫 `Unit` 基類測試（pos, hp, max_hp, size, team, vision_radius, speed, take_damage 返回死亡 bool） (Red)
- [x] Task 1.3: 實作 `Unit` 基類 (`entities/unit.py`) (Green)
- [x] Task 1.4: 撰寫 `Ship` 子類測試（`CombatShip` S/M/L 屬性、`SonarController` 預設關閉、`SpeedMode` 預設普通） (Red)
- [x] Task 1.5: 實作 `CombatShip`、`MiningShip`（含 cargo/assigned_asteroid/state 屬性）、`BuilderShip`（含 assigned_target/building_type/state 屬性）+ `SonarController` + `SpeedMode` (`entities/ship.py`) (Green)
- [x] Task 1.6: 撰寫 `Building` 子類測試（`Mothership` HP 2000、`MiningStation` buffer 屬性、`Turret` 攻擊屬性） (Red)
- [x] Task 1.7: 實作 `Mothership`、`MiningStation`（buffer, station_mine_rate, attached_asteroid）、`Turret` (`entities/building.py`) (Green)
- [x] Task 1.8: 撰寫 `Asteroid` 測試（size S/M/L、revealed flag 預設 False）與 `World` 測試（entity 新增/移除、grid 空間索引查詢） (Red)
- [x] Task 1.9: 實作 `Asteroid` (`entities/asteroid.py`) + `World`（entity 列表、grid 索引）(`core/world.py`) (Green)
- [x] Task 1.10: 實作 `main.py`（GameLoop 60 FPS、相機 WASD + 滑鼠邊緣捲動、左鍵選取、左鍵拖拉框選、右鍵指令、形狀渲染）

---

## Milestone 2: 迷霧戰爭（序列）

> **預期結果：** 全圖純黑，玩家單位周圍可見圓完整顯示，單位離開後轉為半透明（可見地形不見動態單位），DARK 區域絕對不顯示任何資訊
> **驗證方式：** `pytest tests/test_fog.py` 全過；hand test 視覺三態效果

- [x] Task 2.1: 撰寫 `FogMap` 測試（初始全 DARK、update() 後 vision_radius 內變 VISIBLE、單位移開後變 SHROUD、is_visible() 查詢正確） (Red)
- [x] Task 2.2: 實作 `FogMap`（`numpy.ndarray` 存三態、`pygame.surfarray` 映射）(`core/fog.py`) (Green)
- [x] Task 2.3: 撰寫迷霧渲染整合測試（DARK=全黑不透明、SHROUD=半透明黑、VISIBLE=透明；enemy 在 DARK 區不被 draw） (Red)
- [x] Task 2.4: 實作 `FogMap.draw()` + 整合到主渲染管線（渲染順序：地圖 → entity → fog overlay）(Green)
- [x] Task 2.5: 撰寫礦場永久標示測試（Asteroid.revealed=True 後，即使在 SHROUD/DARK 仍顯示標記） (Red)
- [x] Task 2.6: 實作礦場永久標示邏輯（`FogMap` 維護 `revealed_positions` set，draw 時疊加「∞」標籤與小地圖綠色方塊）(Green)

---

## Milestone 3: 聲納系統（序列 → 平行）

> **預期結果：** 對艦艇開啟聲納後每 3 秒自動發射脈衝環；環碰到物體在主視圖閃爍輪廓、小地圖亮白點；移動敵艦在小地圖產生橘色模糊光點；光點均隨時間 fade out
> **驗證方式：** `pytest tests/test_sonar.py` 全過；hand test 主視圖波形與小地圖光點

先序列確立核心資料結構：

- [x] Task 3.1: 撰寫 `SonarController` 測試（toggle on/off、timer 倒數、update() 返回 True 表應發射、關閉時不發射） (Red)
- [x] Task 3.2: 實作 `SonarController`（`core/sonar.py`）(Green)
- [x] Task 3.3: 撰寫 `SpeedMode` 測試（toggle、effective_speed 計算：普通=base、加速=base×1.8、音量計算使用 effective_speed） (Red)
- [x] Task 3.4: 實作 `SpeedMode`（整合到 ship.py，`effective_speed` property）(Green)
- [x] Task 3.5: 撰寫 `ActivePulse` 測試（擴散半徑隨 dt 增長、每 400px 衰減強度、強度 0 消亡、check_hit 偵測環碰到 entity） (Red)
- [x] Task 3.6: 實作 `ActivePulse` + `SonarHit` dataclass (`core/sonar.py`)(Green)
- [x] Task 3.7: 撰寫 `PassiveDetector` 測試（PASSIVE_RADIUS 內偵測移動敵方、音量計算、強度映射、位置加噪、靜止不偵測、己方忽略） (Red)
- [x] Task 3.8: 實作 `PassiveDetector` (`core/sonar.py`)(Green)

### 🔀 可平行工作線

**[A] SonarFX 主視圖特效** — `isolation: worktree`
> 範圍：`ui/sonar_fx.py`
> 依賴：Task 3.6 完成的 `ActivePulse`、`SonarHit` dataclass；`constants.py` 中 `SONAR_HIT_FADE`、光點規格
> 介面契約：`SonarFX.add_pulse(pulse: ActivePulse)`、`SonarFX.add_hit(hit: SonarHit)`、`SonarFX.draw(surface: pygame.Surface, camera_offset: tuple)`
> 驗證方式：`pytest tests/test_sonar_fx.py`（fade 計時正確、強度 1/2/3 對應線寬 1/2/3px、pulse 環半徑隨 age 增長）

- [x] Task 3.9: 撰寫 `SonarFX` 測試（pulse 環繪製半徑、hit flash 強度→線寬、fade out 計時、多脈衝共存） (Red)
- [x] Task 3.10: 實作 `SonarFX`（pulse 環繪製、hit 輪廓閃光 fade 從清晰到模糊）(Green)

**[B] 小地圖聲納光點** — `isolation: worktree`
> 範圍：`ui/minimap.py`
> 依賴：Task 3.6 完成的 `SonarHit` dataclass；`World` entity 列表（M1）
> 介面契約：`Minimap.draw(surface: pygame.Surface, world: World, sonar_hits: list[SonarHit])`；主動 hit→白點半徑 4/8/14px；被動 hit→橘點半徑 4/8/14px
> 驗證方式：`pytest tests/test_minimap.py`（玩家白點、敵方紅點、主動白光點、被動橘光點、fade 計時、世界座標→小地圖座標映射）

- [x] Task 3.11: 撰寫 `Minimap` 測試（單位點渲染、聲納光點顏色/大小/fade、礦場綠色方塊、座標映射） (Red)
- [x] Task 3.12: 實作 `Minimap`（含單位點、聲納光點、礦場標記）(Green)

### 🔗 匯合點
> 驗證方式：合併後 `pytest tests/test_sonar*.py tests/test_minimap.py` 全過；hand test：開啟聲納→3 秒發射脈衝→碰小行星有閃光→小地圖有白點；移動測試艦艇→小地圖橘點出現

- [x] Task 3.13: 合併 [A]、[B] 分支；整合 `SonarController.update()` + `ActivePulse.check_hit()` + `PassiveDetector` 到主迴圈每 frame update；wiring `SonarFX` + `Minimap` 到渲染管線

---

## Milestone 4: 採礦 + 建造系統（序列 → 平行）

> **預期結果：** 採礦船可右鍵指派到小行星→自動採礦→滿艙回母艦卸貨→循環；採礦站無人時自動存礦、有船時停；母艦 2 條序列可同時生產艦艇；建造船可施工並顯示進度
> **驗證方式：** `pytest tests/test_mining.py tests/test_build.py` 全過

先序列確立 ship.py 子類介面（避免平行修改同檔衝突）：

- [x] Task 4.1: 確認 `MiningShip` 完整 state machine 屬性（`state ∈ {IDLE, MOVING_TO_AST, MINING, MOVING_TO_BASE, COLLECTING_STATION}`）與 `BuilderShip` 屬性（`state ∈ {IDLE, MOVING_TO_SITE, BUILDING, WAITING_RESOURCES}`），補全至 `entities/ship.py`（只屬性，邏輯由 system 處理）

### 🔀 可平行工作線

**[A] MiningSystem** — `isolation: worktree`
> 範圍：`systems/mining.py`、`entities/asteroid.py`（attach 邏輯、reveal 整合）
> 依賴：Task 4.1 完成的 `MiningShip` state 屬性；`FogMap.is_visible()`（M2）；`SonarHit`（M3）；`World.entities`（M1）
> 介面契約：`MiningSystem.update(world: World, dt: float)` → 驅動所有 MiningShip state machine；`Asteroid.is_attached_by(ship)` flag；`MiningStation.buffer` 增減
> 驗證方式：`pytest tests/test_mining.py` 全過（至少 10 個 test case 覆蓋下方 Red task）

- [x] Task 4.2: 撰寫 `MiningSystem` 測試（attach 流程、MINE_RATE 每秒 10、cargo 滿→MOVING_TO_BASE、路過站 80px 取礦、站無船時自動採礦 5/s、站有船時停止、buffer 上限 500） (Red)
- [x] Task 4.3: 實作 `MiningSystem`（採礦、cargo 管理、返回母艦路徑、station buffer 邏輯）(Green)
- [x] Task 4.4: 撰寫 `Asteroid.reveal` 測試（`FogMap.is_visible` 為 True 或被 SonarHit 命中 → `revealed=True`；revealed 後 FogMap 加入 `revealed_positions`） (Red)
- [x] Task 4.5: 實作小行星 reveal 邏輯（`MiningSystem.update()` 中每 frame 檢查視野；整合 SonarHit 命中回調）(Green)

**[B] BuildSystem + BuildQueue** — `isolation: worktree`
> 範圍：`systems/build.py`、`entities/building.py`（MiningStation 的 `attached_asteroid` 設定）
> 依賴：Task 4.1 完成的 `BuilderShip` state 屬性；`Building` 子類（M1）；`World.add_entity()`（M1）
> 介面契約：`BuildQueue.enqueue(unit_type, cost, resources) -> bool`；`BuildQueue.update(dt) -> Unit | None`；`BuildSystem.update(world, dt)` → 驅動 BuilderShip state machine
> 驗證方式：`pytest tests/test_build.py` 全過

- [x] Task 4.6: 撰寫 `BuildQueue` 測試（2 條序列各自獨立推進、進度計時到 build_time、完成產出 Unit、佇列上限 4、資源不足拒絕） (Red)
- [x] Task 4.7: 實作 `BuildQueue` + 母艦持有 2 個實例 (`systems/build.py`)(Green)
- [x] Task 4.8: 撰寫 `BuildSystem` 測試（BuilderShip MOVING_TO_SITE→BUILDING、施工進度 dt 累積、HP=0 進度歸零資源不退還、WAITING_RESOURCES 等待資源、完成後建物 add 到 world） (Red)
- [x] Task 4.9: 實作 `BuildSystem`（建造船 state machine、施工進度、建物完成生效）(Green)
- [x] Task 4.10: 撰寫 `MiningStation` attach 測試（施工完成後自動 attach 最近小行星 ≤ 150px；超出範圍時 attached_asteroid=None 且不採礦） (Red)
- [x] Task 4.11: 實作 `MiningStation` 自動 attach 邏輯（在 `BuildSystem` 建物完成時觸發）(Green)

### 🔗 匯合點
> 驗證方式：`pytest tests/test_mining.py tests/test_build.py` 全過；hand test：右鍵指派採礦船→採礦→回母艦；從面板生產建造船→施工→採礦站完工

- [x] Task 4.12: 合併 [A]、[B] 分支，解決衝突；整合 `MiningSystem` + `BuildSystem` 到主迴圈 update；wiring 右鍵點擊小行星→指派採礦船、右鍵地圖→建造船移動指令

---

## Milestone 5: 戰鬥 + 控制面板 + AI（序列 → 平行）

> **預期結果：** 艦艇進入射程自動開火；摧毀敵母艦顯示勝利畫面；選取各類單位出現對應功能面板按鈕；AI 會採礦→建兵→進攻
> **驗證方式：** `pytest tests/test_combat.py tests/test_control_panel.py tests/test_ai.py` 全過；完整 playtest 可勝可敗

先序列完成戰鬥系統（AI 依賴）：

- [x] Task 5.1: 撰寫 `CombatSystem` 測試（進入 attack_range 自動鎖定最近敵方、傷害計算、fire_rate 計時、HP≤0 回傳死亡列表、砲塔攻擊、射程邊界） (Red)
- [x] Task 5.2: 實作 `CombatSystem` (`systems/combat.py`)(Green)
- [x] Task 5.3: 撰寫勝負條件測試（`World.check_win_condition()` → 敵母艦 HP≤0 返回 "player_win"、玩家母艦 HP≤0 返回 "player_lose"、其他返回 None） (Red)
- [x] Task 5.4: 實作勝負判定 + 勝/敗畫面（半透明覆蓋 + 文字「勝利！」/「失敗...」+ 按鍵重啟）(Green)

### 🔀 可平行工作線

**[A] 單位控制面板 UI** — `isolation: worktree`
> 範圍：`ui/control_panel.py`
> 依賴：`Unit`、`Ship`、`Building` 類別（M1）；`SonarController.toggle()`、`SpeedMode.toggle()`（M1/M3）；`BuildQueue.enqueue()`（M4B）；`MiningShip.assigned_asteroid`（M4A）
> 介面契約：`ControlPanel.set_selection(units: list[Unit])`；`ControlPanel.draw(surface: pygame.Surface)`；`ControlPanel.handle_event(event: pygame.Event)` → 呼叫對應 unit method（toggle/command）
> 驗證方式：`pytest tests/test_control_panel.py`（各單位類型生成正確按鈕組、toggle dispatch、母艦序列面板按鈕、框選縮圖列表）

- [x] Task 5.5: 撰寫 `ControlPanel` 測試（`set_selection` 觸發對應按鈕組生成；CombatShip→聲納+速度、MiningShip→聲納+速度+礦場、Mothership→2 條序列面板、Turret→無按鈕；`handle_event` dispatch 到正確 method） (Red)
- [x] Task 5.6: 實作 `ControlPanel` 核心（動態按鈕生成、draw 到畫面下方 160px 區域、handle_event 分發）(Green)
- [x] Task 5.7: 實作各單位面板細節（聲納/速度 toggle 高亮、指派礦場等待狀態、建造選單展開、母艦生產列表含費用+時間、佇列縮圖列表最多 4 格、砲塔攻擊範圍圓繪製、採礦站 buffer 顯示）(Green)

**[B] 敵方 AI 狀態機** — `isolation: worktree`
> 範圍：`ai/enemy.py`
> 依賴：`World.entities`（M1）；`CombatSystem`（Task 5.2）；`MiningSystem`（M4A）；`BuildSystem` + `BuildQueue`（M4B）
> 介面契約：`EnemyAI.update(world: World, dt: float)`；`state ∈ {idle, mining, building, attacking}`；達到 `AI_ATTACK_THRESHOLD = 3` 艘戰艦後切換 attacking
> 驗證方式：`pytest tests/test_ai.py`（狀態轉換邏輯：idle→mining→building→attacking；採礦船指派；建兵觸發；攻擊艦隊集結；全圖可見）

- [x] Task 5.8: 撰寫 `EnemyAI` 測試（狀態轉換條件、採礦船派發、建造序列使用、戰艦數量達門檻→攻擊、attack state 派出所有戰艦） (Red)
- [x] Task 5.9: 實作 `EnemyAI` 狀態機（mining→building→attacking 轉換、簡單艦隊前進邏輯）(Green)

### 🔗 匯合點
> 驗證方式：合併後 `pytest` 全套測試通過；完整 playtest：可選取所有單位→面板正確顯示功能按鈕；AI 主動派兵；擊沉敵母艦→勝利畫面；被打敗→失敗畫面

- [x] Task 5.10: 合併 [A]、[B]；整合 `ControlPanel` + `EnemyAI` 到主迴圈；`CombatSystem` 接入主 update；wiring `check_win_condition` 到主迴圈；全系統 end-to-end 手動測試
