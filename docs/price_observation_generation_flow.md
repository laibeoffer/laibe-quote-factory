# PriceObservation Generation Flow (QF4)

## 目的

`scripts/generate_price_observations_from_rows.py` 讀取 `samples/sample_normalized_quote_rows.json`，
只轉換可代表單筆工項的 `quote_line`，輸出供未來價格觀測彙整流程使用的
`exports_to_raw_warehouse/sample_price_observations.json`，
並把需要人工複核的項目輸出到 `review_queue/sample_price_observation_review_queue.json`。

## 轉換流程

1. 載入資料與設定檔
2. 過濾 `row_role == quote_line` 且 `blocked == false`
3. 逐列建立 `PriceObservation`：
   - `observation_id` 使用 row id 衍生
   - `source_file_id`、`source_row_id`、`source_file_name`、`quote_date`、`observed_year` 等追蹤欄位
   - 單位正規化
   - canonical item 命中
   - 工料分離 scope 判斷
   - 觀測價格與金額留存
4. 依條件判斷是否進入 `review queue`
5. 寫出兩個 sample payload
6. 列印 summary

## 產生欄位

每筆 PriceObservation 必填輸出：

- observation_id
- source_file_id
- source_row_id
- source_file_name
- quote_date
- observed_year
- region_raw
- region_normalized
- trade_category
- canonical_item_code
- canonical_item_name
- item_name_raw
- item_name_normalized
- brand
- model
- spec
- method_tags
- spec_tags
- work_material_scope
- unit_raw
- unit_normalized
- conversion_factor
- observed_unit_price
- normalized_unit_price
- amount_observed
- currency
- confidence
- warnings
- requires_human_review
- created_at
- updated_at
- schema_version
- upload_stage

同時保留 `source_row_id`，以便回溯原始 `raw_quote_row`。

## Safety 規則

- 不輸出正式價格欄位：
  - `unit_price`
  - `formal_price`
  - `approved_price`
  - `pricing_rule_id`
  - `budget_estimate_line_id`
- `observed_unit_price` / `normalized_unit_price` 皆是觀測價，不作為正式單價。

## Review 分流條件

符合任一條件即進入 review queue：

- `canonical_item_code` 為 `null`
- `requires_human_review == true`
- 單位無法辨識（`unit_normalized == UNKNOWN`）
- `work_material_scope == unknown`
- `warnings` 非空

## Work / Material Scope 來源

- 先以 `trade_category` 取預設值（`configs/work_material_rules.json`）
- 再比對例外關鍵字（如磁磚貼工、插座、五金等）
- 低信心情況會偏向 `unknown`，由 review queue 補正

## 觀測到一般價格

本輪僅輸出 sample，未做：

- 時間權重
- 價格區間計算
- 正式定價、Pricing Rule 生成
- 匯出到正式報價流程
