# PriceRange Generation Flow (QF5)

本階段只處理 sample price observations，輸出仍為「候選統計資料」而非正式價格。

## 1. 輸入
- `exports_to_raw_warehouse/sample_price_observations.json`
- `exports_to_raw_warehouse/sample_alias_edge_case_price_observations.json`
- `exports_to_raw_warehouse/sample_alias_negative_context_price_observations.json`
- `configs/time_weight_rules.json`

## 2. 核心規則
- 只聚合 `canonical_item_code` 非空的 observation。
- 以下情況的 observation 不納入正式聚合，但都保留在輸入追蹤中：
  - `requires_human_review = true`
  - `warnings` 非空
  - `upload_stage` 不在 `staging_candidate` / `approved_for_cloud`
  - 包含 `alias_negative_context_hit`
  - 缺 `normalized_unit_price`、缺法定時間資訊、超過 36 個月或價格無效
- 聚合鍵：
  - `canonical_item_code`
  - `unit_normalized`
  - `work_material_scope`
  - `region_normalized`
  - `currency`

## 3. 統計欄位
每組輸出一筆 `PriceRange`，欄位至少包含：
- `price_range_id` / `id`
- `canonical_item_code`
- `canonical_item_name`
- `unit_normalized`
- `work_material_scope`
- `region_normalized`
- `currency`
- `price_min`
- `price_max`
- `price_median`
- `price_weighted_avg`
- `display_unit_price`
- `observation_count`
- `included_observation_count`
- `excluded_observation_count`
- `low_confidence_count`
- `excluded_outlier_count`
- `review_required_count`
- `observation_ids`
- `excluded_observation_ids`
- `warnings`
- `requires_human_review`
- `created_at`
- `updated_at`
- `schema_version`
- `upload_stage`

## 4. 時間權重
- 近 12 個月：weight = `1.0`
- 12–24 個月：weight = `0.7`
- 24–36 個月：weight = `0.5`
- 超過 36 個月：不納入加權平均與統計主體（保留到排除集合）

加權平均公式：
`price_weighted_avg = Σ(normalized_unit_price × weight) / Σ(weight)`

## 5. 中位數 / 顯示價
- `price_median` 使用所有納入觀測值中位數。
- `display_unit_price` 預設用 `price_median`，再依規則四捨五入：
  - `>= 10000` => nearest 500
  - `>= 1000` => nearest 100
  - `>= 100` => nearest 10
  - `< 100` => nearest 1

## 6. Review Queue 條件
將以下任一條件成立的 range 寫入 `sample_price_range_review_queue.json`：
- `included_observation_count < 2`
- `review_required_count > 0`
- `price_min / price_max` 差距過大
- `excluded_observation_count > 0`

## 7. 安全限制
- 不輸出 `unit_price`、`formal_price`、`approved_price`、`pricing_rule_id`、`budget_estimate_line_id`。
- `PriceRange` 是候選統計區間，不是正式單價，不可直接作為最終報價單元價。
