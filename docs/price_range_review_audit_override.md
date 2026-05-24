# QF5.3 PriceRange Review Decision Audit & Override Contract

## Purpose

QF5.3 defines how a reviewed `PriceRange` decision can be overridden while preserving a complete audit trail.

This contract is for candidate-governance only. It does not approve formal prices and does not create `PricingRule`, `MaterialSpec`, `LaborRule`, `BudgetEstimateLine`, renderer output, or customer-facing quote data.

## Relationship To QF5.2

QF5.2 produces a simulated `PriceRange Review Decision` such as:

- `needs_more_observations`
- `needs_unit_review`
- `keep_as_historical_reference`
- `approved_for_cloud`
- `rejected`

QF5.3 does not replace those decisions silently. It records either:

- a preserved decision, when no override exists
- an applied override, when an allowed transition is requested
- a rejected override, when the request is unsafe or invalid

## Override Request Fields

Each override request must include:

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

## Allowed Override Behavior

Allowed transitions are configured in `configs/price_range_override_rules.json`.

Examples:

- `needs_more_observations -> keep_as_historical_reference`
- `needs_unit_review -> keep_as_historical_reference`
- `keep_as_historical_reference -> approved_for_cloud`

Conditional transitions may require stronger evidence. For example:

- `rejected -> approved_for_cloud` requires `senior_manual_override`
- it also requires `override_risk_acknowledged: true`

If the conditional requirement is not met, the override is rejected and the original decision is preserved.

## Reviewed Output Fields

The reviewed output with audit metadata must retain:

- `review_decision`
- `suggested_decision`
- `previous_decision`
- `final_decision`
- `override_applied`
- `override_reason_codes`
- `reviewer_id`
- `reviewed_at`
- `audit_event_id`
- `decision_history`
- `is_simulated_review`

## Audit Event Fields

Every override or preserved decision creates an audit event with:

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

Allowed `event_type` values:

- `override_requested`
- `override_applied`
- `override_rejected`
- `decision_preserved`

## Decision History

`decision_history` is embedded in each reviewed `PriceRange` output so the latest payload remains self-auditing.

Each history entry should include:

- audit event id
- event type
- previous decision
- requested decision
- final decision
- override allowed / applied flags
- reason codes
- reviewer id
- event time
- errors
- warnings

## Safety Rules

QF5.3 must never output:

- `unit_price`
- `formal_price`
- `approved_price`
- `pricing_rule_id`
- `budget_estimate_line_id`
- `material_spec_id`
- `labor_rule_id`
- `formal_material_spec_id`
- `formal_labor_rule_id`

`approved_for_cloud` only means the candidate statistical payload can move to cloud staging or the next review layer. It is not formal pricing approval.

QF5.3 must also keep these flags false:

- `formal_price_generated: false`
- `formal_pricing_rule_generated: false`
- `formal_material_spec_generated: false`
- `formal_labor_rule_generated: false`
- `budget_estimate_line_generated: false`
- `supabase_connected: false`
- `migration_generated: false`

## Validation Expectations

Before publishing QF5.3:

1. Run `python scripts/apply_price_range_review_overrides.py`.
2. Confirm `illegal_override_blocked_count` is greater than zero.
3. Run `python scripts/validate_sample_cloud_payload.py`.
4. Run `python scripts/validate_price_ranges.py`.
5. Confirm all validation summaries report zero forbidden formal pricing fields.
6. Confirm no Supabase, API, migration, renderer, or formal quote path is connected.

## Downstream Boundary

Correct downstream path:

`Quote Factory -> Raw Candidate Warehouse -> Pricing / Method Review -> Budget Engine`

Forbidden direct paths:

- `PriceRange -> Renderer`
- `PriceRange -> BudgetOutputSnapshot`
- `display_unit_price -> BudgetEstimateLine.unit_price`
- `approved_for_cloud -> formal price approval`
