# Works Log — Sonor Prototype

## Milestone 1: 地基（完成）

### 決策記錄

**pygame-ce 取代 pygame**
Python 3.14 尚無官方 pygame wheel，改用 `pygame-ce 2.5.7`（Community Edition），API 完全相容，支援 Python 3.14。

**constants.py 集中所有數值**
所有遊戲參數（單位數值、聲納參數、地圖大小）集中在 `constants.py`，entity class 只做 import，不 hardcode 數字。這讓日後平衡調整只需改一個檔案。

**SonarController / SpeedMode 作為 composition 而非繼承**
掛在 ship 上的 SonarController 和 SpeedMode 是獨立 class instance，而非 mixin 繼承。好處：測試更容易隔離、未來若要序列化狀態也更直接。

**World.entities_in_radius 純 Python 計算**
Prototype 階段 entity 數 < 200，純 Python loop 足夠（< 1ms）。若未來需要效能優化可改 quadtree 或 numpy 向量化，介面不變。

**BuildQueue 在 Mothership 內而非 systems/build.py**
BuildQueue 屬於 Mothership 的狀態，放在 `entities/building.py` 更符合「entity 持有自身狀態」的設計原則。BuildSystem 後續負責 tick BuildQueue.update()。

### 測試結果
- `tests/test_entities.py`: 43 passed
- `tests/test_world.py`: 9 passed
- 合計：**52 passed, 0 failed**

---

## Milestone 2: 迷霧戰爭（完成）

### 決策記錄

**numpy 圓形繪製（向量化）**
`FogMap.update()` 用 `np.meshgrid` + `mask = dx²+dy² ≤ r²` 一次性繪製整個視野圓，避免 Python 逐像素迴圈。3000×3000 地圖上 10 個單位的 fog update 約 3–8ms。

**`render_filter.py` 獨立模組**
「哪些 entity 該繪製」的邏輯抽出為 `should_draw_entity(entity, fog)` 純函式，方便測試、不依賴 pygame Surface。main.py 的渲染迴圈呼叫它做過濾。

**`reveal_asteroids()` 整合在 FogMap**
每 frame fog.update() 後呼叫 `fog.reveal_asteroids(world.asteroids)`，自動將當前 VISIBLE 範圍內的小行星標為 revealed。一旦 revealed，`render_filter` 永遠讓它通過，不再受霧遮蔽。

**FogMap.draw() 使用 SRCALPHA Surface**
DARK 區域用不透明黑（alpha=255），SHROUD 用 alpha=160 的黑色半透明疊加。使用 PixelArray 逐格設色。若效能不足後期可改 numpy surfarray 批次寫入。

### 測試結果
- `tests/test_fog.py`: 14 passed
- `tests/test_fog_render.py`: 11 passed
- M1+M2 合計：**77 passed, 0 failed**

---

## Milestone 3: 聲納系統（完成）

### 決策記錄

**`core/sonar.py` 集中三大聲納類別**
`ActivePulse`、`SonarHit`（dataclass）、`PassiveDetector` 放在 `core/sonar.py`；`SonarController` 與 `SpeedMode` 留在 `entities/ship.py`（composition 掛在 ship 上）。分層明確：core 層處理物理計算，entity 層持有控制狀態。

**ActivePulse 衰減用里程碑計數器**
用 `_decay_milestone` 累加 `PULSE_DECAY_DIST`，避免每 frame 做除法取整數；while 迴圈處理單 frame 內跨越多個閾值的邊界狀況（高幀率下 dt 可能很小，問題不大，但正確性更重要）。

**命中容差 30px**
`check_hit` 的容差選 30px（≈ PULSE_SPEED × 0.15s），使得 60FPS 下脈衝環不會穿過小型目標而漏偵測。

**SonarFX 用暫存 SRCALPHA Surface 繪製環**
每個環和 hit 都畫在獨立的 temp surface 上再 blit，避免 `pygame.draw.circle` 不支援 alpha 的問題，同時能正確實現 fade out 效果。

**Minimap 分離為獨立模組**
`ui/minimap.py` 只接受 `world`、`sonar_hits` 參數，不依賴相機座標——因為小地圖顯示的是完整世界視圖而非相機可見區域。主迴圈傳入 `sonar_hits` 列表（本 frame 偵測到的所有接觸），minimap 自行過濾已過期的 hits。

**主迴圈聲納整合順序**
每 frame 的執行順序：
1. SonarController.update() → 若返回 True 建立 ActivePulse 並加入 SonarFX
2. 對現有 pulses 執行 check_hit → 新 SonarHit 同時加入 SonarFX 與當 frame 的 sonar_hits 列表
3. SonarFX.update(dt) → 推進 pulse 半徑、過期移除
4. PassiveDetector.detect() → 被動偵測，hits 加入兩處
5. 渲染：entity → SonarFX.draw() → fog → minimap.draw()

### 測試結果
- `tests/test_sonar.py`: 35 passed
- `tests/test_sonar_fx.py`: 14 passed
- `tests/test_minimap.py`: 17 passed
- M1+M2+M3 合計：**143 passed, 0 failed**

---

## Milestone 4: 採礦 + 建造系統（完成）

### 決策記錄

**MiningSystem 獨立 system class**
採礦邏輯集中在 `systems/mining.py`，entity 只持有狀態（state, cargo, assigned_asteroid），邏輯與資料分離。BuildSystem 同理。

**Station 採礦：ship 在場就停**
`Asteroid.has_attached_ship()` 是判斷條件。Station 不需要知道哪艘船，只需知道「有沒有船在這顆礦上」——讓 Asteroid 持有 `_attached_ships` list 最自然。

**Station 收礦：MOVING_TO_BASE 途中自動掃過**
MiningShip 在 MOVING_TO_BASE 狀態移動時，`_check_station_collect()` 每 frame 檢查 80px 內是否有 buffer > 0 的 station。不需要額外狀態——途中自動撈。

**reveal_by_hits 掛在 MiningSystem**
Asteroid reveal 邏輯與採礦系統耦合最緊（誰去採礦、誰知道礦的位置），且 hit radius=40px 是估算值，不需要精確匹配。主迴圈每 frame 呼叫一次。

**BuildSystem 完工後自動 attach**
MiningStation 完工時，BuildSystem 立刻掃描 STATION_ATTACH_RADIUS (150px) 內最近小行星。這個邏輯放在 BuildSystem._complete() 比放在 MiningStation.__init__ 更清晰——建物初始化不應有世界查詢副作用。

**STATION_BUILD_TIME、TURRET_BUILD_TIME 加入 constants.py**
M4 前 constants.py 缺少建造時間。補上 STATION_BUILD_TIME=20s、TURRET_BUILD_TIME=30s。

**右鍵指令分流**
右鍵點擊：若點到 Asteroid（30px 內）→ 指派選取的 MiningShip；若點到空地 → BuilderShip 設 assigned_target + building_type="MiningStation"；其他船（CombatShip）走原有的 _target_pos 移動。

### 測試結果
- `tests/test_mining.py`: 14 passed
- `tests/test_asteroid_reveal.py`: 8 passed
- `tests/test_build.py`: 18 passed
- M1+M2+M3+M4 合計：**183 passed, 0 failed**

---

## Milestone 5: 戰鬥 + 控制面板 + AI（完成）

### 決策記錄

**CombatSystem 使用 fire_timer 初始化為 1/fire_rate**
原先 `_fire_timer = 0.0` 導致第一 frame 就開火。改為 `1/fire_rate` 讓所有武裝單位在部署後等一個完整週期才能射擊，行為更自然。Turret 同理。

**World.check_win_condition 處理兩種死亡情境**
母艦可能 (a) hp≤0 但還在 entities list（被 CombatSystem 殺死後移除，但條件先檢查到），或 (b) 已從 world 移除。兩種情境都要能偵測 → 分成兩個掃描段落：先掃 hp≤0，再掃「只有一方存在」。

**ControlPanel 用 dataclass PanelButton**
每個 button 是一個 dataclass，持有 `name`、`rect`、`on_click`（lambda）、`active`（lambda）。on_click 是閉包直接捕捉 unit 引用，避免需要「當前 selection」的全域狀態。

**EnemyAI 極簡四態機**
idle → mining（派採礦船）→ building（推演建造序列）→ attacking（所有戰艦衝向玩家母艦）。AI 不使用霧（全圖可見），只做序列狀態機，無路徑規劃。Prototype 等級夠用，未來可替換。

**ControlPanel 與主 HUD 分離**
ControlPanel 畫在獨立的 160px panel_surf 上，blit 到螢幕底部。原 `_draw_hud` 只保留頂部礦物 bar。這樣 ControlPanel 測試不需要 full screen context。

**重啟按 R**
game_result 不為 None 時顯示半透明 overlay + 勝敗文字 + "Press R to restart"。R 鍵重新呼叫 `_new_game()` 建立全新 world/fog/sonar_fx/enemy_ai。

### 測試結果
- `tests/test_combat.py`: 13 passed
- `tests/test_control_panel.py`: 18 passed
- `tests/test_ai.py`: 9 passed
- 全 Milestone 合計：**223 passed, 0 failed**

---

## Post-M5 Cross-Review 修正

### 決策記錄

**xreview 以兩個獨立 reviewer 並行審查**
orchestrator script 缺失，改為直接派兩個 ddd-reviewer subagent 平行執行，coordinator 驗證 Critical/Important findings 後再套用。

**C1：sonar pulse 強度使用屬性值**
`main.py` 原本 hardcode `strength=2`，改為 `getattr(e, "sonar_strength", 1)`，讓不同大小戰艦的聲納強度正確反映。

**C2：移除 K_s dead code**
`keys[pygame.K_s and 0]` 是無效表達式（`and` 在 Python 返回 0），移除兩行死碼。

**C3：Mothership build_queues 從未被 tick**
`main.py` 缺少對 `build_queues` 的 `q.update(dt)` 呼叫，導致 AI 永遠無法建造戰艦。補上每 frame 的 tick 邏輯與 CombatShip spawn。同時 `systems/mining.py` 的採礦收礦邏輯只處理 TEAM_PLAYER，修正為雙方都適用。

**C4：resources=9999 旁路**
`ControlPanel` 建造按鈕未收到 world 引用，資源檢查 fallback 到 9999（永遠可以造）。修正：`set_selection(units, world=world)` 傳入 world，`_make_enqueue` 使用實際 `world.resources`。

**I1：PassiveDetector 未使用 effective_speed**
被動聲納音量計算使用 `_current_speed` fallback，改為 `speed_mode.effective_speed(speed)`，boost 狀態下的船隻音量才會正確放大。

**I2：COLLECTING_STATION 廢棄狀態**
MiningShip.STATES 和 mining.py 裡的 dead elif 分支都殘留 COLLECTING_STATION，一併移除。

**I3：MOVING_TO_AST None crash**
`assigned_asteroid` 可能為 None 時（採礦船 state 被設定但礦未指派），直接呼叫 `asteroid.pos` 會 crash。加 None guard：`if ship.assigned_asteroid is None: ship.state = "IDLE"; continue`。

**I4：fog.draw() alpha 與效能問題**
原本用 PixelArray 逐格寫 alpha，DARK 區域 alpha=0（透明而非不透明）。改為 numpy surfarray 批次寫入：`pixels_alpha(fog_surf)[:] = alpha.T`，DARK=255 / SHROUD=160 / VISIBLE=0。

### 測試結果
- 8 項修正套用後：**223 passed, 0 failed**

---

## Post-M5 Gameplay 修正（實機測試）

### 決策記錄

**CombatShip 缺少 _target_pos 初始化**
`CombatShip.__init__` 未設 `self._target_pos = None`，導致 `hasattr(e, "_target_pos")` 為 False，右鍵移動命令永遠無效。補上初始化後戰艦可正常移動。

**SonarFX 渲染在霧下方**
原渲染順序：entities → sonar_fx → fog。sonar hit 標記被霧覆蓋而看不見。改為：entities → fog → sonar_fx，讓聲納接觸點顯示在霧上方。

**ControlPanel 按鈕座標系統錯誤**
按鈕 rect 是 panel-local 座標（y≈30），`handle_event` 卻用螢幕絕對座標（y≈590）比對，導致所有按鈕永遠點不到。修正：`ControlPanel(panel_y=560)` 記住自身螢幕位置，`handle_event` 先扣偏移量再比對。同時加 `in_panel()` 防止 panel 區域的點擊穿透到遊戲世界的選取邏輯。

**EnemyAI._tick_mining None crash**
沒有敵方母艦時 `em.pos` 拋 AttributeError。加 `if em is None: return` guard。

**Headless 整合測試**
新增 `tests/test_integration.py`（7 個端對端測試）：smoke、採礦、戰鬥、AI、建造佇列、勝利條件、移動指令。使用 `SDL_VIDEODRIVER=dummy` 無頭執行，模擬完整主循環邏輯。

**視覺回饋補強**
- HP bar 顯示在所有可見單位頭頂；採礦中的 MiningShip 額外顯示藍色貨艙 bar
- 母艦控制面板底部顯示建造佇列進度 bar + 剩餘秒數
- 命中時目標閃紅光 0.3 秒（_hit_flash 屬性）
- PassiveDetector 改為每 1.5 秒偵測一次，減少視覺噪音
- 小地圖移至右上角，避免與底部控制面板重疊

**AI 平衡調整**
- `_startup_timer = 60.0`：開場 60 秒 AI 不行動，給玩家緩衝
- `AI_ATTACK_THRESHOLD = 5`（原 3）：需要更多戰艦才進攻
- 採礦船生成需要消耗 `MINING_SHIP_COST` 資源（原本免費瞬間出現）
- 敵方初始資源 200 解決 AI bootstrap 問題

**Unit Roster 左側面板**
左側 180px 的單位清單，列出所有玩家單位（類型縮寫、HP bar、state）。左鍵點擊選取、Shift+點多選。拖曳選框只在 x > 180 時觸發（避開 roster 區域）。

**母艦建造選項擴充**
新增 MiningShip 和 BuilderShip 的建造按鈕；`MINING_SHIP_BUILD_TIME = 15s`、`BUILDER_SHIP_BUILD_TIME = 20s` 加入 constants.py。母艦的兩條建造佇列均顯示（空閒也顯示「——」）。

### 測試結果
- `tests/test_integration.py`: 7 passed
- 全部合計：**230 passed, 0 failed**
