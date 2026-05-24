# Quote Factory Definition Of Done

## Global Done Rules

A Quote Factory phase is done only when:

- all changed files are inside `laibeoffer/laibe-quote-factory`
- sample payloads remain candidate-only
- validation scripts pass
- forbidden formal fields are absent
- review / audit trail is preserved
- no real Supabase, API, migration, renderer, Excel/PDF, payment, escrow, listing fee, or real AI API is connected
- the completion report is short enough for Deputy Codex to sync to the `laibe-mvp` blackboard

## QF5.3 Done Rules

QF5.3 is done when:

- `docs/price_range_review_audit_override.md` is readable and matches the implemented behavior
- `configs/price_range_override_rules.json` defines allowed and conditional transitions
- `scripts/apply_price_range_review_overrides.py` applies valid overrides and rejects illegal overrides
- `review_queue/sample_price_range_review_overrides.json` includes at least one illegal override sample
- `review_queue/sample_price_range_review_audit_log.json` records applied, rejected, and preserved events
- `exports_to_raw_warehouse/sample_price_ranges_reviewed_with_audit.json` includes final decisions and decision history
- `scripts/validate_sample_cloud_payload.py` validates QF5.3 payloads
- `scripts/validate_price_ranges.py` still passes

Required QF5.3 safety outcomes:

- `illegal_override_blocked_count > 0`
- `formal_price_generated: false`
- `formal_pricing_rule_generated: false`
- `formal_material_spec_generated: false`
- `formal_labor_rule_generated: false`
- `budget_estimate_line_generated: false`
- `supabase_connected: false`
- `migration_generated: false`
- `forbidden_field_hit_count: 0`

## QF5.4 Entry Rules

QF5.4 may start only after QF5.3 is visible in the external Quote Factory repo through a merged commit or open PR that Deputy Codex can verify.

QF5.4 must remain a dry-run / governance contract unless a separate formal Issue explicitly authorizes more.
