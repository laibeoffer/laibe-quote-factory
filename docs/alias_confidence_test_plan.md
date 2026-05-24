# Alias Confidence Test Plan (QF4.1)

本輪測試目標：強化 canonical alias 命中邏輯，避免低信心或負例硬塞 `canonical_item_code`，並驗證雲端 payload 對
`PriceObservation` 的必要欄位檢查。

## 測試資料

- 正式測試樣本：`samples/sample_alias_edge_case_rows.json`
- 行為樣本包含 10 筆，分為：
  - 正例 3 筆
  - 低信心 3 筆
  - 負例 4 筆

## 公式（固定）

對每一筆 row，從可命中的 canonical candidates 中取 alias 命中最高者，別名分數：

1. `alias_score` 初始為 `0`
2. 命中 alias（完整別名字串）：`+0.8`
3. 每個 `positive_context_terms` 命中：`+0.05`，上限 `+0.15`
4. 每個 `negative_context_terms` 命中：`-0.3`
5. 同工程類別：`+0.05`

判定：

- `alias_score >= 0.9`  
  - `canonical_item_code` 自動寫入（`requires_human_review = false`）
- `0.75 <= alias_score < 0.9`  
  - `canonical_item_code` 可保留 candidate
  - `requires_human_review = true`
  - `warnings` 加 `alias_low_confidence`
- `alias_score < 0.75`  
  - `canonical_item_code = null`
  - `requires_human_review = true`
  - `warnings` 加 `alias_unmatched_or_unsafe`

## 負向條件（硬化規則）

- 若有 `negative_context_terms` 命中，不能自動匹配：
  - `requires_human_review = true`
  - `warnings` 加 `alias_negative_context_hit`
  - 不得發生 unsafe auto match（`unsafe_auto_match_count = 0`）

## 驗證面

1. 產生 `sample_alias_edge_case_price_observations.json`
2. 產生 `sample_alias_edge_case_review_queue.json`
3. 用 `validate_sample_cloud_payload.py` 檢查：
   - `PriceObservation` 檔與 review queue 欄位完整性
   - `observation_id` 或 `id`
   - `source_file_id`, `source_row_id`, `created_at`, `updated_at`, `schema_version`, `upload_stage`
   - `observed_unit_price`, `normalized_unit_price`, `unit_raw`, `unit_normalized`, `canonical_item_code`, `requires_human_review`
   - 禁止欄位不得出現：`unit_price`, `formal_price`, `approved_price`, `pricing_rule_id`, `budget_estimate_line_id`

## 風險與邊界

- 低信心結果仍可保留 `canonical_item_code` 以保留人工參考，但必須進 review_queue。
- 低於門檻者不應回填 canonical。
- 既有 `sample_normalized_quote_rows.json` 流程不得中斷，且本地參數化執行仍可覆蓋自訂 input/output。
