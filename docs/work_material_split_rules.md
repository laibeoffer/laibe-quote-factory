# Work/Material Split Rules (QF2)

## 一、region 規則

1. 本批資料預設地區為台北價格。
2. `region_normalized` 預設 `Taipei`，`region_raw` 由來源保存。
3. 本輪只保留地區欄位，不做跨縣市價格調整。
4. 未來外縣市的權重調整屬下一階段模型責任，不在本文件實作。

## 二、work_material_scope 欄位

輸出欄位值僅能為：
- `labor_only`
- `material_only`
- `labor_and_material`
- `equipment_allowance`
- `unknown`

## 三、泥作規則

- 泥作預設：一律視為「工料連做」`labor_and_material`。
- 例外（通常需拆開）：
  - 磁磚鋪貼
  - 大理石門檻
  - 人造石門檻
  - 浴缸安裝
- 例外規則注意：
  - 除門檻外（大理石門檻/人造石門檻）大多採工料分離，尤其高材質工項。
  - 磁磚鋪貼原則上工料分離，且常見不含磁磚材，`work_material_scope` 以 `labor_only` 為先。
  - 當文字顯示含「含材」「含料」「含材料」且高價材質明確，轉為 `labor_and_material`，同時提高信心並保留 review tags。

## 四、水電規則

- 水電預設為 `labor_only`（工料分離）。
- 若描述已把插座、開關、弱電面板分開列示，保留該列為獨立 observation，不強制併入其他材料估值，`work_material_scope = labor_only`。
- 出現高價設備型號但描述為「施作」可視為 `equipment_allowance` 或 review。

## 五、木工規則

- 木工除高價五金以外，預設 `labor_and_material`。
- 高價五金詞彙（例如特定五金、品牌掛勾設備配件）可先歸為 `equipment_allowance`。
- 若為低價通用五金且未明確列價位，保留 `labor_and_material`。

## 六、廚具規則

- 櫃體：`labor_and_material`
- 人造石檯面：`labor_and_material`
- 廚房機器（油煙機、爐具、洗碗機等）與高價五金：`equipment_allowance`

## 七、判斷優先順序

1. 強制規則（明確文字）優先
2. 類別上下文（trade_category）
3. alias / spec / note 提示
4. 歷史觀測（低風險情境可提高 `labor_and_material` 預設）
5. 無法判斷 → `unknown` 並進 review_queue

## 八、低信心保護

- 當描述模糊、金額異常高、或同時命中多規則衝突，須 `requires_human_review = true`。
- 低信心情境不得直接標成 `labor_only` 或 `material_only` 以免污染歷史價格分群。
