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
