# Price Observation Specification (QF2)

## 1. 定義

`PriceObservation` 為非正式、可追溯的歷史價格樣本，不等於最終報價價位，也不直接成為正式 `unit_price`。

## 2. 欄位定義

- `observation_id`
- `source_file_id`
- `source_file_name`
- `quote_date`
- `observed_year`
- `region_raw`
- `region_normalized`
- `trade_category`
- `canonical_item_code`
- `canonical_item_name`
- `item_name_raw`
- `item_name_normalized`
- `brand`
- `model`
- `spec`
- `method_tags`
- `spec_tags`
- `work_material_scope`
- `unit_raw`
- `unit_normalized`
- `conversion_factor`
- `observed_unit_price`
- `normalized_unit_price`
- `amount_observed`
- `currency`
- `confidence`
- `warnings`
- `requires_human_review`

## 3. 欄位規格

- `observation_id`: 唯一識別碼，來源可用 `source_file_id + row_id + hash`。
- `observed_year`: 從 `quote_date` 擷取年份。
- `region_raw`: 來源原始地區文字；`region_normalized` 預設 `Taipei`。
- `work_material_scope`: 來自工料分離規則（`work_material_scope.md`）。
- `method_tags`: 字串陣列，紀錄判斷依據，例如：
  - `header_confident`
  - `alias_match`
  - `unit_m2_normalized`
  - `manual_reviewed`
- `spec_tags`: 字串陣列，紀錄規格特徵：
  - `bathroom`
  - `kitchen`
  - `tile_before`
  - `before_waterproof`
- `conversion_factor`: 單位轉換因子，對應 `unit_raw` 到內部計算或展示單位。
- `normalized_unit_price`: 轉換後可比較價值。
- `warnings`: 來源警示清單。
- `requires_human_review`: 標示是否需人工確認。

## 4. 非正式性條款（硬性）

- `observed_unit_price` / `normalized_unit_price` 僅是「觀測證據價」。
- 不得將它們直接當作 `formal unit_price`。
- 嚴禁輸出 `approved_price` / `pricing_rule_id` / `material_spec` / `labor_spec` / `BudgetEstimateLine` 等正式欄位。

## 5. 輸出邏輯

- 只要 `quantity`、`unit`、`unit_price`（或 `amount`）具可追溯性，就可建立觀測值。
- `low_confidence` 或 `amount_mismatch` 可保留 observation，但需 `requires_human_review=true`。
- 無法辨識 item，保留 raw 字段，`canonical_item_code` 先空值。

## 6. 交接

- `PriceObservation` 用於後續時間加權、區間聚合與使用者顯示。
- 聚合與價格建議僅使用 observation pool，且應排除已被標記為高風險且未確認的值。
