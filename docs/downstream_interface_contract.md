# Downstream Interface Contract (QF5)

## 1. 嚴格邊界
- `laibe_quote_factory` 僅處理候選資料清洗與統計，禁止直接輸出到：
  - `Renderer`
  - Excel/PDF 直接輸出流程
  - `BudgetOutputSnapshot`
  - 成品物流渲染相關輸出
- 本階段不接 Supabase、不接 API、不進行 migration。

## 2. 候選輸出集合（允許）
- `RawQuoteRow`
- `RawCatalogSource`
- `RawCatalogItem`
- `PriceObservation`
- `PriceRange`
- `ReviewQueueItem`

## 3. 非正式性（核心）
- `PriceObservation` 不是正式價格，不是 `PricingRule`。
- `PriceRange` 不是正式價格，不是 `PricingRule`。
- `PriceRange` 不得直接變成 `BudgetEstimateLine.unit_price`。
- `PriceRange` 不得直接進 `customer_view`。
- `observed_unit_price` / `normalized_unit_price` 僅為觀測證據，不能作為單價來源。
- `display_unit_price` 僅為候選顯示，不可直接寫入 `BudgetEstimateLine.unit_price`。

## 4. 下游流程（建議）
```
laibe_quote_factory
  -> Raw Candidate Warehouse
  -> Pricing / Method Review
  -> Budget Engine
  -> BudgetOutputSnapshot
  -> Renderer
```

## 5. 禁止流程（must not）
- `PriceObservation -> Renderer`
- `PriceRange -> Renderer`
- `RawQuoteRow -> Renderer`
- `RawCatalogItem -> BudgetOutputSnapshot`
- `observed_unit_price -> BudgetEstimateLine.unit_price`
- `display_unit_price -> BudgetEstimateLine.unit_price`（without review pass）

## 6. 成品物流可讀入口
- `BudgetOutputSnapshot`
- `RenderedBudgetDocument`

## 7. 驗證與安全
- 所有產出保留 `upload_stage`、`schema_version`、時間戳、追溯欄位。
- 下一流程需另行 review/approval 後，才能轉為正式報價邏輯依據。
