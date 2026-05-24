# Cloud Interface Contract (QF3 Extension)

## 1. 階段邊界

1. 目前階段不上雲，不連接 Supabase，不執行資料庫 migration，不提供 API。
2. 本階段仍輸出本地 JSON（sample 和未來實際 loader 都以 JSON 為主）。
3. 所有資料模型仍只做候選整理，**不產生正式價格**，不建立正式規則、正式材工規格或 BudgetEstimateLine。

## 2. Cloud-ready 目標

所有本地 JSON 必須可視為未來上雲時的 insert payload：

- 欄位名採 `snake_case`
- 每筆資料有穩定 `id`
- 每筆資料有 `created_at`、`updated_at`
- 每筆資料有 `source_file_id`、`source_row_id`（如 row 級資料）
- review 狀態使用 enum，避免自由文字
- price 類欄位保留為觀測值命名，不可使用正式價名詞
- `upload_stage` 明確標示該筆資料目前上雲流程階段

## 3. 觀測價名稱邊界

- `observed_unit_price` / `normalized_unit_price` 代表歷史觀測值（evidence price），不等同正式報價單價。
- 不可在此階段命名為 `unit_price`、`formal_price`、`approved_price`、`pricing_rule_id`。

## 4. Review 狀態枚舉

本輪建議使用下列枚舉值：

- `local_only`
- `staging_candidate`
- `review_required`
- `approved_for_cloud`
- `archived`

每筆資料都應有 `upload_stage`，且值必須在上述集合中。

## 5. 全域欄位預留（所有 sample output 需保留）

每筆可上雲 payload 建議至少包含：

- `id`
- `created_at`
- `updated_at`
- `source_file_id`
- `source_row_id`（row 級資料需要）
- `upload_stage`
- `schema_version`

其中：

- `schema_version` 可用如 `qf3_v1`
- `created_at` 與 `updated_at` 可先採本機固定時間字串或空值（在 schema 與樣本中預留）
- `source_row_id` 用於追溯到原始列；如果目前來源為檔案層資料，可設定為空字串或 `null`

## 6. Cloud table mapping

見 `configs/cloud_table_mapping.json`。其目標是把本地 JSON 對應到未來資料表欄位：

- `quote_source_files`
- `raw_quote_rows`
- `raw_catalog_sources`
- `raw_catalog_items`
- `price_observations`
- `price_ranges`
- `canonical_items`
- `item_aliases`
- `unit_normalization_rules`
- `work_material_rules`
- `quote_review_queue`
- `export_batches`

## 7. 資料分層：GitHub / Supabase / 本機

### GitHub 放

- `docs`
- `configs`
- `scripts`
- `sanitized samples`
- `cloud interface contract`

### Supabase 未來放

- normalized raw quote rows
- price observations
- price ranges
- review queue
- approved canonical items
- cloud-ready raw catalog items

### 本機保留

- `raw_uploads`
- 原始 Excel / PDF / 圖片
- 未清洗客戶資料
- 未去識別廠商資料

## 8. 本輪注意事項

- 不做外部服務操作，不產生實際 DB payload 送出。
- 僅補齊契約與配置描述，確保後續可平滑切換到雲端持久層。  
