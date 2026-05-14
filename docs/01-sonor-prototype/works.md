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
