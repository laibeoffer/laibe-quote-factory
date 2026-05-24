import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
REVIEWED_PATH = ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_ranges_reviewed.json"
OVERRIDES_PATH = ROOT_DIR / "review_queue" / "sample_price_range_review_overrides.json"
RULES_PATH = ROOT_DIR / "configs" / "price_range_override_rules.json"
OUTPUT_PATH = ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_ranges_reviewed_with_audit.json"
AUDIT_LOG_PATH = ROOT_DIR / "review_queue" / "sample_price_range_review_audit_log.json"

SCHEMA_VERSION = "qf5_3_review_audit_v1"
OUTPUT_SCHEMA_VERSION = "qf5_3_reviewed_with_audit_v1"
FORBIDDEN_FIELDS = {
    "unit_price",
    "formal_price",
    "approved_price",
    "pricing_rule_id",
    "budget_estimate_line_id",
}


def now_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_list(value):
    return value if isinstance(value, list) else []


def has_forbidden_fields(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_FIELDS:
                return True
            if has_forbidden_fields(value):
                return True
    elif isinstance(obj, list):
        return any(has_forbidden_fields(item) for item in obj)
    return False


def upload_stage_for_decision(decision):
    if decision == "approved_for_cloud":
        return "approved_for_cloud"
    if decision in {"rejected", "keep_as_historical_reference"}:
        return "archived"
    return "review_required"


def build_rules_index(rules):
    allowed = {
        (item.get("from"), item.get("to"))
        for item in rules.get("allowed_override_transitions", [])
    }
    conditional = {
        (item.get("from"), item.get("to")): item
        for item in rules.get("conditional_override_transitions", [])
    }
    reason_codes = set(rules.get("override_reason_codes", []))
    decisions = set(rules.get("decision_enum", []))
    return allowed, conditional, reason_codes, decisions


def validate_override(override, current_item, rules_index):
    allowed_transitions, conditional_transitions, allowed_reason_codes, allowed_decisions = rules_index
    errors = []
    warnings = []

    price_range_id = override.get("price_range_id")
    previous_decision = override.get("previous_decision")
    requested_decision = override.get("requested_decision")
    reason_codes = set(safe_list(override.get("override_reason_codes")))

    if not current_item:
        errors.append("price_range_id_not_found")
    else:
        current_decision = current_item.get("review_decision")
        if previous_decision != current_decision:
            warnings.append(f"previous_decision_mismatch: current={current_decision}")

    if previous_decision not in allowed_decisions:
        errors.append(f"previous_decision_invalid:{previous_decision}")
    if requested_decision not in allowed_decisions:
        errors.append(f"requested_decision_invalid:{requested_decision}")
    if not price_range_id:
        errors.append("missing_price_range_id")
    if not override.get("override_id"):
        errors.append("missing_override_id")
    if not override.get("reviewer_id"):
        errors.append("missing_reviewer_id")
    if not override.get("requested_at"):
        errors.append("missing_requested_at")
    if not override.get("schema_version"):
        errors.append("missing_schema_version")
    if not reason_codes:
        errors.append("missing_override_reason_codes")

    unknown_reason_codes = sorted(reason_codes - allowed_reason_codes)
    if unknown_reason_codes:
        errors.append(f"unknown_override_reason_codes:{','.join(unknown_reason_codes)}")

    transition = (previous_decision, requested_decision)
    transition_allowed = transition in allowed_transitions
    conditional_rule = conditional_transitions.get(transition)

    if not transition_allowed and conditional_rule:
        required_reason = conditional_rule.get("requires_reason_code")
        requires_ack = bool(conditional_rule.get("requires_override_risk_acknowledged"))
        has_required_reason = required_reason in reason_codes
        has_ack = bool(override.get("override_risk_acknowledged"))
        if has_required_reason and (not requires_ack or has_ack):
            transition_allowed = True
        else:
            if required_reason and not has_required_reason:
                errors.append(f"conditional_transition_missing_reason_code:{required_reason}")
            if requires_ack and not has_ack:
                errors.append("conditional_transition_missing_risk_acknowledgement")

    if not transition_allowed:
        errors.append(f"override_transition_not_allowed:{previous_decision}->{requested_decision}")

    if has_forbidden_fields(override):
        errors.append("forbidden_formal_price_field_detected")

    return not errors, errors, warnings


def build_audit_event(override, current_item, final_decision, override_allowed, override_applied, errors, warnings, event_type):
    price_range_id = override.get("price_range_id") or (current_item or {}).get("price_range_id")
    override_id = override.get("override_id", "no-override-id")
    return {
        "audit_event_id": f"audit-{override_id}",
        "id": f"audit-{override_id}",
        "price_range_id": price_range_id,
        "event_type": event_type,
        "previous_decision": override.get("previous_decision"),
        "requested_decision": override.get("requested_decision"),
        "final_decision": final_decision,
        "override_allowed": override_allowed,
        "override_applied": override_applied,
        "override_reason_codes": safe_list(override.get("override_reason_codes")),
        "reviewer_id": override.get("reviewer_id"),
        "reviewer_note": override.get("reviewer_note"),
        "event_time": now_ts(),
        "errors": errors,
        "warnings": warnings,
        "schema_version": SCHEMA_VERSION,
    }


def build_preserved_event(item):
    price_range_id = item.get("price_range_id") or item.get("id")
    final_decision = item.get("review_decision")
    return {
        "audit_event_id": f"audit-preserved-{price_range_id}",
        "id": f"audit-preserved-{price_range_id}",
        "price_range_id": price_range_id,
        "event_type": "decision_preserved",
        "previous_decision": final_decision,
        "requested_decision": final_decision,
        "final_decision": final_decision,
        "override_allowed": False,
        "override_applied": False,
        "override_reason_codes": [],
        "reviewer_id": item.get("reviewer_id"),
        "reviewer_note": "No override request for this PriceRange; original QF5.2 review decision preserved.",
        "event_time": now_ts(),
        "errors": [],
        "warnings": [],
        "schema_version": SCHEMA_VERSION,
    }


def history_entry_from_event(event):
    return {
        "audit_event_id": event.get("audit_event_id"),
        "event_type": event.get("event_type"),
        "previous_decision": event.get("previous_decision"),
        "requested_decision": event.get("requested_decision"),
        "final_decision": event.get("final_decision"),
        "override_allowed": event.get("override_allowed"),
        "override_applied": event.get("override_applied"),
        "override_reason_codes": safe_list(event.get("override_reason_codes")),
        "reviewer_id": event.get("reviewer_id"),
        "event_time": event.get("event_time"),
        "errors": safe_list(event.get("errors")),
        "warnings": safe_list(event.get("warnings")),
    }


def build_output_item(item, event):
    previous_decision = item.get("review_decision")
    final_decision = event.get("final_decision") or previous_decision
    output = dict(item)
    output["review_decision"] = final_decision
    output["suggested_decision"] = item.get("suggested_decision") or previous_decision
    output["previous_decision"] = previous_decision
    output["final_decision"] = final_decision
    output["override_applied"] = bool(event.get("override_applied"))
    output["override_reason_codes"] = safe_list(event.get("override_reason_codes"))
    output["reviewer_id"] = event.get("reviewer_id") or item.get("reviewer_id")
    output["reviewed_at"] = event.get("event_time") or item.get("reviewed_at")
    output["audit_event_id"] = event.get("audit_event_id")
    output["decision_history"] = [history_entry_from_event(event)]
    output["is_simulated_review"] = bool(item.get("is_simulated_review", True))
    output["schema_version"] = OUTPUT_SCHEMA_VERSION
    output["upload_stage"] = upload_stage_for_decision(final_decision)
    output["requires_human_review"] = final_decision != "approved_for_cloud"
    output["updated_at"] = event.get("event_time") or item.get("updated_at")
    return output


def apply_overrides(reviewed_items, overrides, rules):
    rules_index = build_rules_index(rules)
    items_by_id = {item.get("price_range_id") or item.get("id"): item for item in reviewed_items}
    override_by_range = {}
    audit_log = []

    for override in overrides:
        price_range_id = override.get("price_range_id")
        current_item = items_by_id.get(price_range_id)
        allowed, errors, warnings = validate_override(override, current_item, rules_index)
        final_decision = current_item.get("review_decision") if current_item else override.get("previous_decision")
        event_type = "override_rejected"
        override_applied = False

        if allowed and current_item:
            final_decision = override.get("requested_decision")
            event_type = "override_applied"
            override_applied = True
            override_by_range[price_range_id] = build_audit_event(
                override,
                current_item,
                final_decision,
                True,
                True,
                errors,
                warnings,
                event_type,
            )
        else:
            audit_log.append(
                build_audit_event(
                    override,
                    current_item,
                    final_decision,
                    False,
                    False,
                    errors,
                    warnings,
                    event_type,
                )
            )

    output = []
    for item in reviewed_items:
        price_range_id = item.get("price_range_id") or item.get("id")
        event = override_by_range.get(price_range_id)
        if event is None:
            event = build_preserved_event(item)
        audit_log.append(event)
        output.append(build_output_item(item, event))

    return output, audit_log


def build_summary(reviewed_items, overrides, output, audit_log):
    allowed_count = sum(1 for event in audit_log if event.get("event_type") == "override_applied")
    rejected_count = sum(1 for event in audit_log if event.get("event_type") == "override_rejected")
    applied_count = allowed_count
    final_counts = Counter(item.get("final_decision") for item in output)
    return {
        "input_reviewed_price_range_count": len(reviewed_items),
        "override_request_count": len(overrides),
        "override_allowed_count": allowed_count,
        "override_rejected_count": rejected_count,
        "override_applied_count": applied_count,
        "final_approved_for_cloud_count": final_counts.get("approved_for_cloud", 0),
        "final_keep_as_historical_reference_count": final_counts.get("keep_as_historical_reference", 0),
        "final_rejected_count": final_counts.get("rejected", 0),
        "audit_event_count": len(audit_log),
        "illegal_override_blocked_count": rejected_count,
        "formal_price_generated": False,
        "formal_pricing_rule_generated": False,
        "budget_estimate_line_generated": False,
        "supabase_connected": False,
        "migration_generated": False,
    }


def main():
    reviewed_items = load_json(REVIEWED_PATH)
    overrides = load_json(OVERRIDES_PATH)
    rules = load_json(RULES_PATH)

    output, audit_log = apply_overrides(reviewed_items, overrides, rules)
    write_json(OUTPUT_PATH, output)
    write_json(AUDIT_LOG_PATH, audit_log)

    summary = build_summary(reviewed_items, overrides, output, audit_log)
    print("price range review override audit summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if has_forbidden_fields(output) or has_forbidden_fields(audit_log):
        raise SystemExit("forbidden formal price field detected")


if __name__ == "__main__":
    main()
