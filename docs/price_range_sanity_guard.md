# PriceRange Sanity Guard (QF5.1)

`PriceRange` is still candidate statistics. It must remain reviewable, traceable, and blocked from becoming a formal price without downstream approval.

## Required Group Key
Every `PriceRange` must keep the full grouping identity:
- `canonical_item_code`
- `unit_normalized`
- `work_material_scope`
- `region_normalized`
- `currency`

The same values must also be repeated as `group_key_summary` for human review:
`canonical_item_code | unit_normalized | work_material_scope | region_normalized | currency`

## Display Null Reasons
If `display_unit_price` is `null`, at least one `display_null_reason_codes` value is required:
- `no_included_observations`
- `all_observations_excluded`
- `requires_human_review`
- `missing_price_data`

Null display values are acceptable for candidate payloads only when the reason is explicit.

## Review Reasons
Review queue reason codes should be stable and readable:
- `insufficient_observation_count`
- `has_excluded_observations`
- `source_observations_require_review`
- `price_span_too_large`
- `outlier_observed`
- `cross_unit_review_required`

Each range must enter review when:
- `included_observation_count < 2`
- `excluded_observation_count > 0`
- `review_required_count > 0`
- cross-unit review is required

## Multi-Group Canonical Items
The same `canonical_item_code` may appear in more than one `PriceRange` only when the group key differs. Common safe reasons:
- different `unit_normalized`
- different `work_material_scope`
- different `region_normalized`
- different `currency`

The generator must not merge M2 and PING automatically. If both units appear for the same canonical item, all affected M2/PING ranges must be marked with `cross_unit_review_required`.

## Numeric Guards
When price statistics exist:
- `price_min <= price_median <= price_max`
- `price_min <= price_weighted_avg <= price_max`
- `display_unit_price >= price_min * 0.5`
- `display_unit_price <= price_max * 1.5`

## Forbidden Fields
`PriceRange` and its review queue must never contain:
- `unit_price`
- `formal_price`
- `approved_price`
- `pricing_rule_id`
- `budget_estimate_line_id`

`display_unit_price` is not a formal unit price. It is only a rounded candidate statistic for review.
