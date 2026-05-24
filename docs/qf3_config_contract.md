# QF3 Config Contract

本文件定義 QF3 規則參數化設定檔的介面與基本驗證規格。目的在於將 QF2 的規則文件落地為可讀取配置，並在不解析大量真實報價單的前提下進行一致性驗證。

## 1. 目標

- 不直接修改主專案（`C:\laibe_project`）
- 不產生正式價格、不建立正式價格規則
- 僅維持候選清洗階段的規則設定

## 2. 設定檔清單

- `configs/header_aliases.json`
- `configs/item_alias_dictionary.json`
- `configs/unit_normalization_rules.json`
- `configs/work_material_rules.json`
- `configs/price_observation_schema.json`
- `configs/time_weight_rules.json`
- `configs/equipment_allowance_rules.json`

## 3. 驗證原則

1. 每個 JSON 檔必須可解析。
2. 必要欄位必須存在且型別正確。
3. `item_alias_dictionary` 必須含 `canonical_item_code` 與 `aliases`。
4. `unit_normalization_rules` 必須包含坪/M2 換算能力。
5. `work_material_rules` 必須包含 `default_region: Taipei`。
6. `time_weight_rules` 必須有 0-12、12-24、24-36 月權重。
7. 驗證結果輸出為 summary + 錯誤清單（若有）。

## 4. Summary 欄位（腳本輸出）

- `config_file_count`
- `valid_config_count`
- `error_count`
- `warning_count`
- `canonical_item_count`
- `unit_rule_count`
- `work_material_exception_count`
- `formal_price_generated: false`
- `formal_pricing_rule_generated: false`
- `budget_estimate_line_generated: false`

## 5. 邊界註記

- `observed_unit_price`、`normalized_unit_price` 僅為 Price Observation，非正式 `unit_price`。
- 未知欄位、未決定條件與低信心情境需保留 review flag，不得直接升級為正式規則。
