import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
PRICE_RANGES_PATH = ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_ranges.json"
REVIEW_QUEUE_PATH = ROOT_DIR / "review_queue" / "sample_price_range_review_queue.json"
DECISION_RULES_PATH = ROOT_DIR / "configs" / "price_range_review_decision_rules.json"
DECISIONS_PATH = ROOT_DIR / "review_queue" / "sample_price_range_review_decisions.json"
OUTPUT_PATH = ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_ranges_reviewed.json"

REVIEWER_ID = "manual_reviewer_placeholder"
SCHEMA_VERSION = "qf5_2_v1"
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


def safe_list(value):
    return value if isinstance(value, list) else []


def suggested_decision_for(price_range, review_item):
    reason_codes = set(safe_list(price_range.get("warnings"))) | set(safe_list(review_item.get("review_reason_codes")))
    display_null_reasons = set(safe_list(price_range.get("display_null_reason_codes"))) | set(
        safe_list(review_item.get("display_null_reason_codes"))
    )

    if has_forbidden_fields(price_range) or has_forbidden_fields(review_item):
        return "rejected", ["forbidden_field_hit"]

    if "invalid_price_order" in reason_codes:
        return "rejected", ["invalid_price_order"]

    if "cross_unit_review_required" in reason_codes:
        return "needs_unit_review", ["cross_unit_review_required"]

    if price_range.get("work_material_scope") == "unknown" or review_item.get("work_material_scope") == "unknown":
        return "needs_scope_review", ["work_material_scope_unknown"]

    if not price_range.get("canonical_item_code") and not review_item.get("canonical_item_code"):
        return "needs_alias_review", ["canonical_item_missing"]

    if price_range.get("display_unit_price") is None and "all_observations_excluded" in display_null_reasons:
        return "keep_as_historical_reference", sorted(display_null_reasons)

    if price_range.get("included_observation_count", 0) < 2 or review_item.get("included_observation_count", 0) < 2:
        return "needs_more_observations", ["insufficient_observation_count"]

    if price_range.get("display_unit_price") is None:
        return "needs_more_observations", sorted(display_null_reasons or {"missing_price_data"})

    return "approved_for_cloud", ["candidate_statistics_reviewed"]


def build_decision(price_range, review_item):
    suggested_decision, reasons = suggested_decision_for(price_range, review_item)
    price_range_id = price_range.get("price_range_id") or review_item.get("price_range_id")
    decided_at = now_ts()
    return {
        "decision_id": f"decision-{price_range_id}",
        "id": f"decision-{price_range_id}",
        "price_range_id": price_range_id,
        "reviewer_id": REVIEWER_ID,
        "decision": suggested_decision,
        "suggested_decision": suggested_decision,
        "decision_reason_codes": reasons,
        "reviewer_note": "Simulated sample review for QF5.2 contract validation only.",
        "decided_at": decided_at,
        "source_observation_ids": safe_list(price_range.get("observation_ids")),
        "excluded_observation_ids": safe_list(price_range.get("excluded_observation_ids"))
        or safe_list(review_item.get("excluded_observation_ids")),
        "upload_stage": "review_required",
        "schema_version": SCHEMA_VERSION,
        "is_simulated_review": True,
    }


def build_sample_decisions(price_ranges, review_queue):
    ranges_by_id = {item.get("price_range_id") or item.get("id"): item for item in price_ranges}
    decisions = []
    for review_item in review_queue:
        price_range_id = review_item.get("price_range_id") or review_item.get("id")
        price_range = ranges_by_id.get(price_range_id)
        if not price_range:
            continue
        decisions.append(build_decision(price_range, review_item))
    return decisions


def decision_upload_stage(decision):
    value = decision.get("decision")
    if value == "approved_for_cloud":
        return "approved_for_cloud"
    if value in {"rejected", "keep_as_historical_reference"}:
        return "archived"
    return "review_required"


def apply_decisions(price_ranges, decisions):
    decisions_by_range = {item.get("price_range_id"): item for item in decisions}
    reviewed = []
    for price_range in price_ranges:
        price_range_id = price_range.get("price_range_id") or price_range.get("id")
        decision = decisions_by_range.get(price_range_id)
        item = dict(price_range)
        if decision:
            item["review_decision"] = decision.get("decision")
            item["reviewed_at"] = decision.get("decided_at")
            item["reviewer_id"] = decision.get("reviewer_id")
            item["review_reason_codes"] = safe_list(decision.get("decision_reason_codes"))
            item["is_simulated_review"] = bool(decision.get("is_simulated_review"))
            item["upload_stage"] = decision_upload_stage(decision)
            item["requires_human_review"] = decision.get("decision") != "approved_for_cloud"
            item["updated_at"] = now_ts()
        else:
            item["review_decision"] = None
            item["reviewed_at"] = None
            item["reviewer_id"] = None
            item["review_reason_codes"] = []
            item["is_simulated_review"] = False
        reviewed.append(item)
    return reviewed


def build_summary(price_ranges, decisions, reviewed):
    counts = Counter(item.get("decision") for item in decisions)
    return {
        "input_price_range_count": len(price_ranges),
        "decision_count": len(decisions),
        "approved_for_cloud_count": counts.get("approved_for_cloud", 0),
        "rejected_count": counts.get("rejected", 0),
        "needs_more_observations_count": counts.get("needs_more_observations", 0),
        "needs_unit_review_count": counts.get("needs_unit_review", 0),
        "needs_scope_review_count": counts.get("needs_scope_review", 0),
        "needs_alias_review_count": counts.get("needs_alias_review", 0),
        "keep_as_historical_reference_count": counts.get("keep_as_historical_reference", 0),
        "reviewed_output_count": len(reviewed),
        "formal_price_generated": False,
        "formal_pricing_rule_generated": False,
        "budget_estimate_line_generated": False,
        "supabase_connected": False,
        "migration_generated": False,
    }


def main():
    price_ranges = load_json(PRICE_RANGES_PATH)
    review_queue = load_json(REVIEW_QUEUE_PATH)
    load_json(DECISION_RULES_PATH)

    decisions = build_sample_decisions(price_ranges, review_queue)
    write_json(DECISIONS_PATH, decisions)

    reviewed = apply_decisions(price_ranges, decisions)
    write_json(OUTPUT_PATH, reviewed)

    summary = build_summary(price_ranges, decisions, reviewed)
    print("price range review decision summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if has_forbidden_fields(decisions) or has_forbidden_fields(reviewed):
        raise SystemExit("forbidden formal price field detected")


if __name__ == "__main__":
    main()
