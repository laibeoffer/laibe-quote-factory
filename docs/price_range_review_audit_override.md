# QF5.3 PriceRange Review Decision Audit & Override Contract

本文件定義 `PriceRange` 人工覆核 override 的 audit trail 與安全邊界。

## 1. Override 用途

Override 用於記錄人工 reviewer 在 QF5.2 `suggested_decision` 之後，基於領域判斷、單位確認、scope 確認或資料來源品質判斷，要求調整候選統計資料的 review decision。

Override 的目的只有：

- 保留人工覆核理由。
- 保留決策歷史。
- 讓 Raw Candidate Warehouse 可以知道某筆候選統計資料為何被保留、封存或允許上雲等待後續 review。

## 2. 非正式定價聲明

Override 不是正式價格核准。

即使 override 將 `final_decision` 設為 `approved_for_cloud`，也只代表「候選統計資料可上雲進入 Raw Candidate Warehouse / Pricing Review」，不代表：

- 正式價格。
- 正式 PricingRule。
- 正式 MaterialSpec。
- 正式 LaborRule。
- BudgetEstimateLine。
- 正式報價。
- 可交付客戶的預算或合約金額。

`approved_for_cloud` 仍只代表候選統計資料可上雲，不是正式定價核准。

## 3. 禁止事項

Override 不得：

- 產生正式價格。
- 產生正式 PricingRule。
- 產生正式 MaterialSpec。
- 產生正式 LaborRule。
- 產生 BudgetEstimateLine。
- 刪除原始 review reason。
- 刪除原始 `suggested_decision`。
- 覆寫或抹除 PriceObservation 原始證據。
- 連接 Supabase。
- 產生 migration。
- 進入 Renderer / Excel / PDF / BudgetOutputSnapshot。

## 4. 必備 Audit 欄位

每筆 override request 至少必須保留：

- `override_id`
- `price_range_id`
- `previous_decision`
- `requested_decision`
- `reviewer_id`
- `override_reason_codes`
- `reviewer_note`
- `override_risk_acknowledged`
- `requested_at`
- `is_simulated_review`
- `schema_version`

每筆套用後的 reviewed output 至少必須保留：

- `review_decision`
- `suggested_decision`
- `previous_decision`
- `final_decision`
- `override_applied`
- `override_reason_codes`
- `reviewer_id`
- `reviewed_at`
- `decision_history`
- `is_simulated_review`

每筆 audit event 至少必須保留：

- `audit_event_id`
- `price_range_id`
- `event_type`
- `previous_decision`
- `requested_decision`
- `final_decision`
- `override_allowed`
- `override_applied`
- `override_reason_codes`
- `reviewer_id`
- `reviewer_note`
- `event_time`
- `errors`
- `warnings`
- `schema_version`

## 5. 原始理由保留

Override 不得刪除原始 review reason。

套用 override 時，output 必須保留：

- 原始 `review_reason_codes`
- 原始 `suggested_decision`
- `previous_decision`
- `final_decision`
- `decision_history`

若 override 未被允許，必須寫入 audit log，但不得改變該筆 PriceRange 的 final decision。

## 6. Decision History

`decision_history` 應記錄每次決策事件，例如：

- `decision_preserved`
- `override_applied`
- `override_rejected`

每個 history entry 應包含 event id、時間、reviewer、previous decision、requested decision、final decision、reason codes、warnings/errors。

## 7. Safety Summary

QF5.3 script summary 必須明確輸出：

- `formal_price_generated: false`
- `formal_pricing_rule_generated: false`
- `budget_estimate_line_generated: false`
- `supabase_connected: false`
- `migration_generated: false`

若未來任何流程需要把候選統計資料轉成正式定價，必須另開正式 Pricing Review / PricingRule 任務，本 contract 不授權該行為。
