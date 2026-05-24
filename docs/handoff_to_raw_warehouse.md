# RawQuoteRow -> Raw Candidate Warehouse 交接規格（QF1）

## 1. 目標

`RawQuoteRow` 僅負責把不同來源報價列轉成可溯源、可覆核的候選資料。  
這份規格定義如何轉成 `RawCatalogSource` 與 `RawCatalogItem`，並保持「候選價不為正式價」的邊界。

## 2. RawQuoteRow 轉 RawCatalogSource

`RawCatalogSource` 主要對應一次上傳檔案的來源資訊與掃描結果摘要。

### 對應欄位

- `source_file_id` -> `raw_catalog_source.source_file_id`
- `source_file_name` -> `raw_catalog_source.source_file_name`
- `source_type` -> `raw_catalog_source.source_type`
- `sheet_name` -> `raw_catalog_source.sheet_name`
- `project_name` -> `raw_catalog_source.project_name`
- `quote_date` -> `raw_catalog_source.quote_date`
- 可加總：
  - `rows_count`: `RawQuoteRow` 的列數（含 header/subtotal/total）
  - `blocked_count`: `blocked=true` 的列數
  - `review_count`: `requires_human_review=true` 的列數

`RawCatalogSource` 僅做來源追蹤，不儲存任何正式價格判斷。

## 3. RawQuoteRow 轉 RawCatalogItem

`RawCatalogItem` 只接收可輸出的候選列，不包含 total/subtotal/empty/header 總額類訊息。

### 可輸出欄位（最小映射）

- `source_file_id` <- `RawQuoteRow.source_file_id`
- `trade_category` <- `trade_category_normalized` 或 `trade_category_raw`
- `item_name` <- `item_name_normalized` 或 `item_name_raw`
- `brand` <- `brand_normalized` 或 `brand_raw`
- `model` <- `model_normalized` 或 `model_raw`
- `spec` <- `spec_normalized` 或 `spec_raw`
- `unit` <- `unit_normalized` 或 `unit_raw`
- `quantity` <- `quantity_normalized` 或 `quantity_raw`
- `currency` <- `currency_normalized` 或 `currency_raw`
- `observation` <- `note_normalized` / `note_raw`
- `parse_state` <- `parse_warnings`, `requires_human_review`, `confidence`
- `evidence` -> `unit_price_observed`, `amount_observed`, `row_id`, `source_file_name`, `row_index`

## 4. 哪些 row_role 不輸出

以下 row_role 不輸出到 `RawCatalogItem`：

- `trade_category_header`（僅作分類上下文）
- `subtotal`（彙總行）
- `total`（總計行）
- `empty`（空列）
- `note`（純文字註記行）
- `unknown`（除非先完成辨識並轉為 `quote_line`）

`quote_line` 才是可輸出對象（在未 blocked 時）。

## 5. observed price 的角色

- `unit_price_observed`、`amount_observed` 僅為「證據值」。  
- 實作時需保留來源與欄位對應關係，供後續人工與後續流程核對。  
- 不得直接當成最終價格欄位，亦不得進行自動上傳為正式價的轉換。

## 6. 為什麼不能直接變正式單價

1. `RawQuoteRow` 是候選清洗層，資料常含缺欄位、備註條件、口語描述。  
2. 一旦直接升級為正式單價，會繞過：工程分類確認、單位標準化、人工作業審核。  
3. 因此 `RawQuoteRow` 到 `RawCatalogItem` 只保留「可追溯證據」與「人工作業旗標」，不提供可直接套單的價格承諾。

## 7. 禁止項重申

- 不可直接修改 `C:\laibe_project`。  
- 不可建立正式 `PricingRule`、`MaterialSpec`、`LaborRule`、`BudgetEstimateLine`。  
- 不可直接做正式報價結果輸出。  
- 不可使用 `RAG`、`AI API`、`資料庫 migration`。  
