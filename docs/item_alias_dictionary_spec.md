# Item Alias Dictionary Specification (QF2)

## 目標

建立可追溯的品名正規化規則：同義叫法先映射到 `canonical item`，但不允許低信心硬合併。  
此規格輸出到 `PriceObservation.canonical_item_code` 和 `canonical_item_name`，並保留原始 `item_name_raw`。

## 一、資料欄位

每筆 alias 規則至少包含：
- `canonical_item_code`
- `canonical_item_name`
- `aliases`: 同義詞清單
- `must_exclude_if_contains`: 排除條件關鍵字
- `boost_if_contains`: 強化條件關鍵字
- `category_hint`：工別提示（如 `mud_work`, `carpentry`, `electricity`）
- `min_confidence`: 最低可自動採納信心
- `needs_review_when`: 建議轉 review 的條件

## 二、核心判斷流程

1. 先對 `item_name_raw + note_raw` 做關鍵詞抽取。
2. 對每個 canonical 條目計算:
   - 基礎命中（alias 關鍵字命中）
   - 排除條件衝突
   - 強化條件加分
3. 使用加總分數決定匹配項：
   - 高於 `min_confidence`：可自動歸類
   - 介於 `min_confidence / 2` 到 `min_confidence`：暫不歸類，入 review
   - 低於下限：不歸類，保留 raw 名稱

## 三、示例規則

### 泥作牆面粗底打底

- `canonical_item_code`: `MASONRY_WALL_BASE_PREP`
- `canonical_item_name`: `泥作牆面粗底打底`
- `aliases`:
  - 泥作粗底
  - 泥作粗胚
  - 牆面打底
  - 粉粗底
  - 水泥砂漿打底
  - 壁面粗底
- `must_exclude_if_contains`:
  - 油漆
  - 批土
  - 木作
  - 矽酸鈣板
- `boost_if_contains`:
  - 浴室
  - 廚房
  - 濕區
  - 防水前
  - 貼磚前
- `min_confidence`: 0.78
- `needs_review_when`:
  - 只命中 1 個 alias 且含「防水」否則不高於 0.55
  - 含 `notes` 強修飾詞但未命中明確工別

## 四、不得無腦合併規則

- 命中任意 `must_exclude_if_contains` 則禁止歸到該 canonical item，轉到 review 判定。
- 如同時命中兩個 canonical 目標且信心差距 < 0.12，輸出 review。
- 含「門牌/門禁/木門/開關/衛浴設備/燈具」等高歧義詞，要求較高門檻（+0.2）才能自動歸類。

## 五、低信心處理

- 低信心時不得直接確定 canonical，只寫 `canonical_item_code: null`、`canonical_item_name: null` 或保守保留最接近值。
- 必須在警示欄位加入：
  - `item_alias_low_confidence`
  - `needs_human_confirmation`
- 仍保留 `item_name_raw`，不得覆蓋。

## 六、可追溯性要求

- 每次 alias 決策需保留 match log：
  - 命中詞
  - 分數
  - 排除詞
  - 是否入 Review
- 在 `metadata` 中保留 `item_alias_match` 供後續審核與迭代調整。
