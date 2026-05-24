# Time-Weighted Price Range Specification (QF2)

## 1. 目標

基於近三年的 `PriceObservation` 生成價格區間，不建立絕對價，而是輸出可回溯的統計值：
- `price_min`
- `price_max`
- `price_median`
- `price_weighted_avg`
- `display_unit_price`
- `observation_count`
- `low_confidence_count`
- `excluded_outlier_count`

## 2. 數據範圍

- 僅使用近三年（36 個月）內的 `PriceObservation`。
- 同一 `canonical_item_code + unit_normalized + region_normalized + trade_category` 聚合。
- 來源保留 `observed_year` 與 `quote_date`，用於權重與追蹤。

3. 時間權重

- 0–12 個月：`1.0`
- 12–24 個月：`0.7`
- 24–36 個月：`0.5`

權重採半開區間，以「當前日期」為參考。

## 4. 統計計算

- `price_min`：樣本 `normalized_unit_price` 最小值
- `price_max`：樣本 `normalized_unit_price` 最大值
- `price_median`：中位數
- `price_weighted_avg`：加權平均
  - `sum(price * time_weight) / sum(time_weight)`（僅對符合觀測、未被排除者）
- `observation_count`：原始納入樣本數
- `low_confidence_count`：`confidence < 門檻` 或有重點 warning 的樣本數
- `excluded_outlier_count`：被標記為待排除的樣本數（不直接刪除原始資料）

## 5. outlier 處理

- 不直接刪除過高/過低樣本。
- 先標記：
  - `price_outlier_high`
  - `price_outlier_low`
- 是否排除改為 review policy：
  - 被排除樣本不進加權計算，仍保留於 observation pool（可供稽核回放）
  - 原因與證據需加入警示欄位

## 6. display_unit_price

- 顯示價格可使用：
  - `price_median`（偏穩健）
  - 或 `price_weighted_avg`（偏近期）
- 對使用者輸出前必須四捨五入（以元為單位，可含顯示精度欄位控制）
- Raw observation 保持高精度，不得在 pool 中覆蓋原始小數值。

## 7. 不建立正式價格

- 任何 `display_unit_price` 都只是展示建議區間，不是正式報價值。
- 不產生正式規則或 BudgetEstimateLine。
