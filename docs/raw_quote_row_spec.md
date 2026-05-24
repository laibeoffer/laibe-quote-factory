# RawQuoteRow 規格文件（QF1）

## 1. 用途

`RawQuoteRow` 是報價清洗工廠（Quote Factory）中「單筆報價列」的中介資料模型。  
它接收原始表列（raw row）後，先完成欄位清理、欄位標準化與可疑度標記，供人工作業與後續 `RawQuoteRow -> Raw Catalog` 的交接流程使用。  
此階段不建立任何正式價格、不建立正式規則，不做正式報價邏輯。

## 2. 欄位定義

| 欄位 | 說明 | 型別 | 必填 |
|---|---|---|---|
| `row_id` | 每筆來源列唯一識別碼 | `string` | 是 |
| `source_file_id` | 上傳檔案批次識別碼 | `string` | 是 |
| `source_file_name` | 上傳檔名 | `string` | 是 |
| `source_type` | 來源型態：`excel` / `csv` / `pdf` / `manual_text` | `string` | 是 |
| `sheet_name` | 工作表名稱（若來源為表格式） | `string` | 否 |
| `row_index` | 來源中的原始列號 | `integer` | 是 |
| `project_name` | 專案名稱（原始欄位） | `string` | 否 |
| `quote_date` | 報價日期（原始字串） | `string` | 否 |
| `trade_category_raw` | 原始工程分類文字 | `string` | 否 |
| `trade_category_normalized` | 標準化工程分類 | `string` | 否 |
| `item_name_raw` | 原始品項文字 | `string` | 否 |
| `item_name_normalized` | 標準化品項名稱 | `string` | 否 |
| `brand_raw` | 原始品牌 | `string` | 否 |
| `brand_normalized` | 標準化品牌 | `string` | 否 |
| `model_raw` | 原始型號/規格代號 | `string` | 否 |
| `model_normalized` | 標準化型號/規格代號 | `string` | 否 |
| `spec_raw` | 原始規格描述 | `string` | 否 |
| `spec_normalized` | 標準化規格描述 | `string` | 否 |
| `unit_raw` | 原始單位 | `string` | 否 |
| `unit_normalized` | 標準化單位（例如 `m2`、`m`、`pcs`、`set`） | `string` | 否 |
| `quantity_raw` | 原始數量字串 | `string` | 否 |
| `quantity_normalized` | 規範化後數量 | `number` | 否 |
| `unit_price_raw` | 原始單價字串 | `string` | 否 |
| `unit_price_observed` | 視覺/文字抽取到的單價（證據價），可為 `null` | `number` | 否 |
| `amount_raw` | 原始小計字串 | `string` | 否 |
| `amount_observed` | 規範化後小計（證據金額） | `number` | 否 |
| `currency_raw` | 原始幣別字串 | `string` | 否 |
| `currency_normalized` | 標準幣別（`TWD`/`USD` 等） | `string` | 否 |
| `note_raw` | 原始備註文字 | `string` | 否 |
| `note_normalized` | 標準化備註 | `string` | 否 |
| `row_role` | 列角色：`trade_category_header` / `quote_line` / `subtotal` / `total` / `note` / `empty` / `unknown` | `string` | 是 |
| `confidence` | 解析自信度 0~1 的分數 | `number` | 否 |
| `parse_warnings` | 解析警示清單（可多值） | `array[string]` | 否 |
| `requires_human_review` | 是否需人工覆核 | `boolean` | 否 |
| `blocked` | 是否阻擋輸出到 Raw Candidate Warehouse | `boolean` | 否 |
| `blocked_reason` | 阻擋原因清單 | `array[string]` | 否 |

## 3. 欄位型別

`row_id`, `source_file_id`, `source_file_name`, `source_type`, `sheet_name`, `project_name`, `quote_date`, `trade_category_raw`, `trade_category_normalized`, `item_name_raw`, `item_name_normalized`, `brand_raw`, `brand_normalized`, `model_raw`, `model_normalized`, `spec_raw`, `spec_normalized`, `unit_raw`, `unit_normalized`, `unit_price_raw`, `amount_raw`, `currency_raw`, `currency_normalized`, `note_raw`, `note_normalized`, `row_role` 使用 `string`。  
`row_index`, `quantity_normalized` 及 `quantity_raw` 類似欄位中可含字元時保留字串；可解析者以 `quantity_normalized` 存數值。  
`unit_price_observed`, `amount_observed`, `confidence` 使用 `number`。  
`parse_warnings`, `blocked_reason` 使用 `array[string]`。  
`requires_human_review`, `blocked` 使用 `boolean`。

## 4. 必填 / 選填

必填欄位為：`row_id`, `source_file_id`, `source_file_name`, `source_type`, `row_index`, `row_role`。  
其餘欄位視有無可用值填入。  
沒有足夠欄位可解析時，`row_role` 可以先設為 `unknown`，但若是小計、合計、空列要固定對應到對應角色並設定相關阻擋規則。

## 5. 清洗前後差異

清洗前（raw）集中保留原始可見文字，保留拼寫差異與排版污染。  
清洗後（normalized）會做：

1. 單位標準化（例如 `坪`→`坪`, `平`→`坪`，`尺`→`ft`, `口`→`outlet` 需再人工審核確認）。  
2. 數字與金額正規化，去除逗號、空白、貨幣符號，轉為數字。  
3. 日期與幣別正規化。  
4. 缺漏與衝突欄位註記到 `parse_warnings` 與 `requires_human_review`。  
5. 對明顯不可輸出的列（如合計、小計、空列）以 `blocked` 明確標示。

## 6. parse_warnings 規則（至少需支援）

以下 warning 值必須可被輸出：
- `missing_trade_category`
- `missing_item_name`
- `missing_unit`
- `missing_quantity`
- `missing_unit_price`
- `missing_amount`
- `amount_mismatch`
- `subtotal_row`
- `total_row`
- `merged_cell_suspected`
- `note_mixed_in_item_name`
- `unit_unrecognized`
- `currency_missing`
- `low_confidence`

其他 warning 可用於實作擴充（例：`manual_mark`, `date_parsed_from_context`）。

## 7. `requires_human_review` 規則（至少）

若符合下列任一條件，`requires_human_review = true`：

- 缺 `item_name`（`missing_item_name`）
- 缺 `unit`（`missing_unit`）
- 缺價格（`missing_unit_price` 或 `unit_price_raw` 無法轉數字）
- `amount` 與 `quantity * unit_price` 不一致（允許合理四捨五入/精度誤差）
- `trade_category_normalized` 不在已知工程類別清單
- `unit_normalized` 無法辨識（`unit_unrecognized`）
- 備註包含：`另估`、`視現場`、`未含`、`不含`

可同時搭配 `parse_warnings` 輸出原因，便於人工審核 UI 呈現。

## 8. `blocked` 規則（至少）

- `row_role = total`  
- `row_role = subtotal`  
- `row_role = empty`  
- `amount` 為負值且未能辨識為可接受扣抵語意（如「已列入上方小計」但未標註明確扣抵原因）  
- 無法辨識任何品名（`item_name_raw`/`item_name_normalized` 為空且非摘要欄位）  

`blocked = true` 的列不直接進入 RawCandidate 匯出清單，需改由人工作業或後續規則補齊。

## 9. 輸出給 Raw Candidate Warehouse

輸出目標只走「候選」層級，不可當正式資料：

1. 先以未 blocked 且 `row_role = quote_line` 的列進行輸出候選組裝。  
2. 將 `unit_price_observed`、`amount_observed` 轉成 `RawCatalogItem` 的 `evidence` 欄位參考來源，不作為正式 `unit_price`。  
3. `trade_category_normalized` 對應到分類欄位，`item_name_normalized`、`spec_normalized`、`brand_normalized`、`model_normalized` 提供文字證據。  
4. 低可信度、缺欄位或包含警示的列保留 `requires_human_review=true`，但可視情況先輸出供後續人工補全。

## 10. 明確禁止

- 不得在 QF1 直接產生正式價格。  
- `unit_price_observed` 僅能被視為「候選證據價」，不得直接當成最終正式單價。  
- 不得建立正式 `PricingRule`、`MaterialSpec`、`LaborRule`、`BudgetEstimateLine`。  
- 不得直接修改 `C:\laibe_project`。  
