import json
from collections import defaultdict
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
PRICE_RANGE_PATH = ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_ranges.json"
REVIEW_QUEUE_PATH = ROOT_DIR / "review_queue" / "sample_price_range_review_queue.json"

GROUP_KEY_FIELDS = [
    "canonical_item_code",
    "unit_normalized",
    "work_material_scope",
    "region_normalized",
    "currency",
]

DISPLAY_NULL_REASON_CODES = {
    "no_included_observations",
    "all_observations_excluded",
    "requires_human_review",
    "missing_price_data",
}

FORBIDDEN_FIELDS = {
    "unit_price",
    "formal_price",
    "approved_price",
    "pricing_rule_id",
    "budget_estimate_line_id",
    "material_spec_id",
    "labor_rule_id",
    "formal_material_spec_id",
    "formal_labor_rule_id",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def to_num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def scan_forbidden_fields(obj):
    hits = []
    stack = [("$", obj)]
    while stack:
        path, current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if key in FORBIDDEN_FIELDS:
                    hits.append(f"{path}.{key}")
                stack.append((f"{path}.{key}", value))
        elif isinstance(current, list):
            for idx, item in enumerate(current):
                stack.append((f"{path}[{idx}]", item))
    return hits


def group_key(price_range):
    return tuple(price_range.get(field) for field in GROUP_KEY_FIELDS)


def expected_group_key_summary(price_range):
    return " | ".join(str(price_range.get(field, "")) for field in GROUP_KEY_FIELDS)


def validate_price_order(price_range):
    values = [
        to_num(price_range.get("price_min")),
        to_num(price_range.get("price_median")),
        to_num(price_range.get("price_max")),
        to_num(price_range.get("price_weighted_avg")),
    ]
    price_min, price_median, price_max, weighted_avg = values
    if any(v is None for v in values):
        return True
    return price_min <= price_median <= price_max and price_min <= weighted_avg <= price_max


def validate_display_price(price_range):
    display = to_num(price_range.get("display_unit_price"))
    price_min = to_num(price_range.get("price_min"))
    price_max = to_num(price_range.get("price_max"))
    if display is None or price_min is None or price_max is None:
        return True
    return display >= price_min * 0.5 and display <= price_max * 1.5


def main():
    price_ranges = load_json(PRICE_RANGE_PATH)
    review_queue = load_json(REVIEW_QUEUE_PATH)

    review_ids = {item.get("price_range_id") or item.get("id") for item in review_queue if isinstance(item, dict)}
    by_canonical = defaultdict(list)
    for item in price_ranges:
        if isinstance(item, dict):
            by_canonical[item.get("canonical_item_code")].append(item)

    summary = {
        "price_range_count": len(price_ranges),
        "review_queue_count": len(review_queue),
        "display_null_count": 0,
        "missing_display_null_reason_count": 0,
        "multi_group_same_canonical_count": 0,
        "cross_unit_review_required_count": 0,
        "invalid_price_order_count": 0,
        "invalid_display_price_count": 0,
        "insufficient_observation_count": 0,
        "forbidden_field_hit_count": 0,
        "formal_price_generated": False,
        "formal_pricing_rule_generated": False,
        "formal_material_spec_generated": False,
        "formal_labor_rule_generated": False,
        "budget_estimate_line_generated": False,
    }

    errors = []

    for canonical_item_code, rows in by_canonical.items():
        unique_group_keys = {group_key(row) for row in rows}
        if len(rows) > 1 and len(unique_group_keys) > 1:
            summary["multi_group_same_canonical_count"] += 1

        units = {row.get("unit_normalized") for row in rows}
        if "M2" in units and "PING" in units:
            for row in rows:
                if row.get("unit_normalized") in {"M2", "PING"}:
                    warnings = set(row.get("warnings", []))
                    if "cross_unit_review_required" in warnings:
                        summary["cross_unit_review_required_count"] += 1
                    else:
                        errors.append(f"{row.get('price_range_id')} missing cross_unit_review_required")

    for price_range in price_ranges:
        price_range_id = price_range.get("price_range_id") or price_range.get("id")

        missing_group_fields = [field for field in GROUP_KEY_FIELDS if not price_range.get(field)]
        if missing_group_fields:
            errors.append(f"{price_range_id} missing group fields: {', '.join(missing_group_fields)}")

        if price_range.get("group_key_summary") != expected_group_key_summary(price_range):
            errors.append(f"{price_range_id} has invalid group_key_summary")

        if price_range.get("display_unit_price") is None:
            summary["display_null_count"] += 1
            reasons = set(price_range.get("display_null_reason_codes", []))
            if not reasons.intersection(DISPLAY_NULL_REASON_CODES):
                summary["missing_display_null_reason_count"] += 1
                errors.append(f"{price_range_id} missing display null reason")

        if price_range.get("included_observation_count", 0) < 2:
            summary["insufficient_observation_count"] += 1
            if price_range_id not in review_ids:
                errors.append(f"{price_range_id} missing review queue item for insufficient observations")

        if price_range.get("excluded_observation_count", 0) > 0 and price_range_id not in review_ids:
            errors.append(f"{price_range_id} missing review queue item for excluded observations")

        if price_range.get("review_required_count", 0) > 0 and price_range_id not in review_ids:
            errors.append(f"{price_range_id} missing review queue item for source review requirement")

        if not validate_price_order(price_range):
            summary["invalid_price_order_count"] += 1
            errors.append(f"{price_range_id} has invalid price order")

        if not validate_display_price(price_range):
            summary["invalid_display_price_count"] += 1
            errors.append(f"{price_range_id} has invalid display price")

    forbidden_hits = scan_forbidden_fields(price_ranges) + scan_forbidden_fields(review_queue)
    summary["forbidden_field_hit_count"] = len(forbidden_hits)
    if forbidden_hits:
        errors.extend([f"forbidden field found: {hit}" for hit in forbidden_hits])

    print("price range validation summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        print(json.dumps({"errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
