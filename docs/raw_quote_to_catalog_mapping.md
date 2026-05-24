# RawQuoteRow -> RawCatalog 映射規格（QF2）

## 1. RawQuoteRow 轉 RawCatalogSource

一個 `RawQuoteRow` 批次通常對應到一個 `RawCatalogSource`。  
Source 是「輸入檔層」的容器，承載來源檔資訊與整體信度，不包含正式價格邏輯。

### 映射

- `id` ← `source_file_id`
- `source_type` ← `source_type`
- `source_name` ← `source_file_name`
- `source_date` ← `quote_date`（第一筆可用日期）
- `source_note` ← `project_name`（第一筆可用專案名稱）
- `region` ← `null`
- `currency` ← `currency_normalized`（缺值 fallback `TWD`）
- `source_reliability` ← `"unverified"`（固定）
- `raw_items` ← 由合格 `quote_line` 組成的 `RawCatalogItem[]`

## 2. RawQuoteRow 轉 RawCatalogItem

- `id` ← `row_id`
- `source_id` ← `source_file_id`
- `row_index` ← `row_index`
- `raw_category` ← `trade_category_normalized`
- `raw_name` ← `item_name_normalized` fallback `item_name_raw`
- `raw_brand` ← `brand_normalized` fallback `brand_raw`
- `raw_model` ← `model_normalized` fallback `model_raw`
- `raw_spec` ← `spec_normalized` fallback `spec_raw`
- `raw_unit` ← `unit_normalized` fallback `unit_raw`
- `raw_quantity` ← `quantity_normalized`
- `raw_unit_price` ← `unit_price_observed`
- `raw_amount` ← `amount_observed`
- `raw_currency` ← `currency_normalized` fallback `TWD`
- `raw_note` ← `note_normalized` fallback `note_raw`
- `raw_text` ← 串接 `trade_category_raw + " / " + item_name_raw + " / " + unit_raw + " / " + note_raw`
- `effective_date` ← `quote_date`
- `region` ← `null`
- `vendor_name` ← `null`
- `metadata` 包含：  
  - `source_file_name`
  - `sheet_name`
  - `row_role`
  - `parse_warnings`
  - `requires_human_review`
  - `confidence`

## 3. 輸出條件

### 只輸出 `quote_line`

- `row_role = quote_line` 才可轉為 `RawCatalogItem`。

### 不輸出 row_role

- `trade_category_header`
- `subtotal`
- `total`
- `note`
- `empty`
- `unknown`

### blocked 規則

- 任何 `blocked = true` 的列，不輸出成 `RawCatalogItem`。
- `blocked = true` 的列仍保留在 review/validation 日誌，待人工處理。

### 人工覆核

- `requires_human_review = true` 的 `quote_line` 可輸出，但需保留 `metadata` 標記。
- `parse_warnings` 非空的列可輸出，但需保留警示，並同步進入 `review_queue`。

## 4. 價格欄位邊界

- `unit_price_observed` / `amount_observed` 僅作為**觀測證據**。
- 嚴禁輸出以下欄位（QF2 階段）：
  - `unit_price`
  - `formal_price`
  - `approved_price`
  - `pricing_rule_id`
- 嚴禁建立正式報價/正式規則模型。
