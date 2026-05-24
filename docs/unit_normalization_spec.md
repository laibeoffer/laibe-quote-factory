# Unit Normalization Specification (QF2)

## 目標

單位標準化保證可比對與彙總，但不丟失原始表達。  
本階段不建立正式價格，只產出可追溯的觀測價欄位。

## 一、欄位要求

每列必須輸出：
- `unit_raw`（原始值）
- `unit_normalized`（標準化值）
- `conversion_factor`（轉為內部標準計量單位的轉換係數）
- `observed_unit_price`（原始單價）
- `normalized_unit_price`（轉為內部或對外展示一致單位後價格）

## 二、原則

1. `unit_raw` 必須完整保留，不得直接覆蓋。
2. `unit_normalized` 僅做歸一處理，例如：
   - `坪` → `PING`
   - `M2` / `㎡` / `m2` → `M2`
   - `CM` / `cm` → `CM`
   - `M` / `m` → `M`
3. `conversion_factor` 要對應 `unit_normalized` 與內部計算單位關係，台灣輸出常用單位保留：
   - 內部計算可用 `M2`
   - 對外保留台灣常見：`坪`, `尺`, `口`, `盞`, `組`, `式`, `間`
4. 無法辨識單位要進 review_queue 並記錄 warning `unit_unrecognized`。

## 三、坪與 M2 互轉

- `1 坪 = 3.305785 M2`  
- `1 M2 = 0.3025 坪`
- 當輸入單位為坪，且 `normalized_unit_price` 需以 M2 計算時：
  - `normalized_unit_price = observed_unit_price / 3.305785`
- 當輸入單位為 M2，轉為坪展示時：
  - `display_unit_price = observed_unit_price * 3.305785`

## 四、支援單位清單

- `CM`
- `M`
- `尺`
- `才`
- `口`
- `盞`
- `組`
- `式`
- `間`
- `坪`
- `M2`

未列入支援清單且可轉換性不明者，標記為需人工確認。

## 五、價值欄位規範

```text
observed_unit_price: 來源單價文字清理後數值
unit_raw: 原始單位字串
unit_normalized: 內部標準化單位
normalized_unit_price: 已轉換到目標展示/聚合單位後的單價
```

若缺少 `unit_price_raw`，`observed_unit_price` 可為 `null`，不得阻斷整列；需加 warning `missing_unit_price`。

## 六、轉換與一致性

- `quantity_normalized` 建議以 `unit_normalized` 基礎對齊；若原始資料為混用單位，需拆分為多列或走人工檢核。
- `amount` 若與 `observed_unit_price * quantity` 不吻合，標記 `amount_mismatch` 並進入 review。

## 七、輸出策略（本區域）

- 內部計算可預設 M2，並保留原始台灣單位上下文（例如坪、尺）。
- 對展示層可按 `unit_normalized` 回填當地常用顯示單位，避免跨專案誤解。
