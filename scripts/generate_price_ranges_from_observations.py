import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_OBSERVATION_PATHS = [
    ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_observations.json",
    ROOT_DIR / "exports_to_raw_warehouse" / "sample_alias_edge_case_price_observations.json",
    ROOT_DIR / "exports_to_raw_warehouse" / "sample_alias_negative_context_price_observations.json",
]
DEFAULT_OUTPUT_PATH = ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_ranges.json"
DEFAULT_REVIEW_OUTPUT_PATH = ROOT_DIR / "review_queue" / "sample_price_range_review_queue.json"
TIME_WEIGHT_CONFIG_PATH = ROOT_DIR / "configs" / "time_weight_rules.json"

SCHEMA_VERSION = "qf3_v1"
ALLOWED_STAGES = {"staging_candidate", "approved_for_cloud"}
FORBIDDEN_FIELDS = {
    "unit_price",
    "formal_price",
    "approved_price",
    "pricing_rule_id",
    "budget_estimate_line_id",
}


def now_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def to_num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_str(value):
    return "" if value is None else str(value)


def normalize_key_value(value):
    return safe_str(value).strip().lower()


def parse_date(value):
    raw = safe_str(value).strip()
    if not raw:
        return None
    if len(raw) >= 7 and len(raw) <= 10:
        try:
            return datetime.fromisoformat(raw[:10]).date()
        except Exception:
            pass
    try:
        return datetime.fromisoformat(raw).date()
    except Exception:
        pass
    return None


def months_diff_late(a, b):
    return (a.year - b.year) * 12 + (a.month - b.month)


def weight_for_months(age_months, config):
    if age_months is None:
        return None
    if age_months <= 12:
        return to_num(config.get("time_weights", {}).get("recent_0_12_months_weight", 1.0))
    if age_months <= 24:
        return to_num(config.get("time_weights", {}).get("months_12_24_weight", 0.7))
    if age_months <= 36:
        return to_num(config.get("time_weights", {}).get("months_24_36_weight", 0.5))
    return None


def safe_round_price(value):
    if value is None:
        return None
    if value >= 10000:
        step = 500
    elif value >= 1000:
        step = 100
    elif value >= 100:
        step = 10
    else:
        step = 1
    return round(value / step) * step


def has_forbidden_fields(obj, forbidden):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in forbidden:
                return True
            if has_forbidden_fields(value, forbidden):
                return True
    elif isinstance(obj, list):
        return any(has_forbidden_fields(item, forbidden) for item in obj)
    return False


def pct(sorted_values, percent):
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = (len(sorted_values) - 1) * percent / 100.0
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return sorted_values[int(idx)]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (idx - lo)


def build_price_range_id(group_key, seq):
    canonical_item_code, unit_normalized, work_material_scope, region_normalized, currency = group_key
    return f"pr-{seq:03d}-{canonical_item_code}-{unit_normalized}-{work_material_scope}-{region_normalized}-{currency}".replace(" ", "")


def build_group_key_summary(group_key):
    canonical_item_code, unit_normalized, work_material_scope, region_normalized, currency = group_key
    return " | ".join([canonical_item_code, unit_normalized, work_material_scope, region_normalized, currency])


def display_null_reasons(stats, included_count, excluded_count, observation_count, review_required_count):
    if stats.get("display_unit_price") is not None:
        return []

    reasons = []
    if included_count == 0:
        reasons.append("no_included_observations")
    if observation_count > 0 and excluded_count == observation_count:
        reasons.append("all_observations_excluded")
    if review_required_count > 0:
        reasons.append("requires_human_review")
    if stats.get("price_min") is None or stats.get("price_median") is None or stats.get("price_weighted_avg") is None:
        reasons.append("missing_price_data")
    return sorted(set(reasons))


def review_reasons_for_range(price_range):
    reasons = []
    if price_range.get("included_observation_count", 0) < 2:
        reasons.append("insufficient_observation_count")
    if price_range.get("excluded_observation_count", 0) > 0:
        reasons.append("has_excluded_observations")
    if price_range.get("review_required_count", 0) > 0:
        reasons.append("source_observations_require_review")
    if "price_span_too_large" in price_range.get("warnings", []):
        reasons.append("price_span_too_large")
    if "outlier_observed" in price_range.get("warnings", []):
        reasons.append("outlier_observed")
    if "cross_unit_review_required" in price_range.get("warnings", []):
        reasons.append("cross_unit_review_required")
    if price_range.get("display_unit_price") is None:
        reasons.extend(price_range.get("display_null_reason_codes", []))
    return sorted(set(reasons))


def flatten_observations(paths):
    observations = []
    for p in paths:
        payload = load_json(p)
        if isinstance(payload, list):
            observations.extend(payload)
    return observations


def is_negative_context(obs):
    for value in obs.get("warnings", []) or []:
        if isinstance(value, str) and value == "alias_negative_context_hit":
            return True
    return False


def build_summary():
    return {
        "input_observation_count": 0,
        "filtered_observation_count": 0,
        "generated_price_range_count": 0,
        "review_range_count": 0,
        "excluded_observation_count": 0,
        "group_count": 0,
        "forbidden_field_hit_count": 0,
        "formal_price_generated": False,
        "formal_pricing_rule_generated": False,
        "budget_estimate_line_generated": False,
        "supabase_connected": False,
        "migration_generated": False,
    }


def outlier_bounds(values):
    if len(values) < 4:
        return None, None
    values = sorted(values)
    q1 = pct(values, 25)
    q3 = pct(values, 75)
    if q1 is None or q3 is None:
        return None, None
    iqr = q3 - q1
    if iqr < 0:
        iqr = 0
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def range_statistics(values, weights):
    valid_pairs = [(v, w) for v, w in zip(values, weights) if v is not None and w is not None and w > 0]
    if not valid_pairs:
        return {
            "price_min": None,
            "price_max": None,
            "price_median": None,
            "price_weighted_avg": None,
            "display_unit_price": None,
        }
    valid_values = [v for v, _ in valid_pairs]
    total_w = sum(w for _, w in valid_pairs)
    weighted_sum = sum(v * w for v, w in valid_pairs)
    return {
        "price_min": min(valid_values),
        "price_max": max(valid_values),
        "price_median": statistics.median(valid_values) if valid_values else None,
        "price_weighted_avg": weighted_sum / total_w if total_w else None,
        "display_unit_price": safe_round_price(statistics.median(valid_values)) if valid_values else None,
    }


def run_generation(input_paths=None, output_path=DEFAULT_OUTPUT_PATH, review_output_path=DEFAULT_REVIEW_OUTPUT_PATH):
    paths = [Path(p) for p in input_paths] if input_paths else DEFAULT_OBSERVATION_PATHS
    observations = flatten_observations(paths)
    config = load_json(TIME_WEIGHT_CONFIG_PATH)
    now = datetime.now(timezone.utc).date()

    summary = build_summary()
    summary["input_observation_count"] = len(observations)
    grouped = defaultdict(list)

    for idx, obs in enumerate(observations):
        if not isinstance(obs, dict):
            summary["filtered_observation_count"] += 1
            continue

        canonical_code = safe_str(obs.get("canonical_item_code")).strip()
        if not canonical_code:
            summary["filtered_observation_count"] += 1
            continue

        unit_normalized = safe_str(obs.get("unit_normalized", "")).strip() or "UNKNOWN"
        scope = safe_str(obs.get("work_material_scope", "")).strip() or "unknown"
        region = safe_str(obs.get("region_normalized", "")).strip() or "Taipei"
        currency = safe_str(obs.get("currency", "TWD")).strip() or "TWD"

        quote_date = parse_date(obs.get("quote_date"))
        age_months = None
        if quote_date is not None:
            age_months = abs(months_diff_late(now, quote_date))
        weight = weight_for_months(age_months, config) if obs.get("normalized_unit_price") is not None else None

        normalized_unit_price = to_num(obs.get("normalized_unit_price"))
        requires_review = bool(obs.get("requires_human_review"))
        warnings = [str(w) for w in (obs.get("warnings") or []) if isinstance(w, str)]
        has_warnings = len(warnings) > 0
        stage = safe_str(obs.get("upload_stage"))
        negative_context = is_negative_context(obs)

        exclusion_reasons = []
        if weight is None:
            exclusion_reasons.append("outside_time_weight_scope")
        if requires_review:
            exclusion_reasons.append("requires_human_review")
        if has_warnings:
            exclusion_reasons.append("has_warnings")
        if negative_context:
            exclusion_reasons.append("alias_negative_context_hit")
        if stage not in ALLOWED_STAGES:
            exclusion_reasons.append("upload_stage_not_allowed")

        if normalized_unit_price is None or normalized_unit_price <= 0:
            exclusion_reasons.append("invalid_normalized_unit_price")

        grouped[(canonical_code, unit_normalized, scope, region, currency)].append(
            {
                "observation_id": safe_str(obs.get("observation_id")) or safe_str(obs.get("id")),
                "canonical_item_name": obs.get("canonical_item_name"),
                "normalized_unit_price": normalized_unit_price,
                "weight": weight,
                "requires_human_review": requires_review,
                "warnings": warnings,
                "exclusion_reasons": exclusion_reasons,
                "quote_date": quote_date.isoformat() if quote_date else None,
            }
        )

    price_ranges = []
    for seq, (group_key, rows) in enumerate(sorted(grouped.items(), key=lambda item: str(item[0])), 1):
        if not rows:
            continue

        observation_count = len(rows)
        summary["group_count"] += 1
        canonical_item_code, unit_normalized, work_material_scope, region_normalized, currency = group_key
        canonical_item_name = next((r.get("canonical_item_name") for r in rows if r.get("canonical_item_name")), None)

        included_rows = [r for r in rows if not r["exclusion_reasons"]]
        excluded_rows = [r for r in rows if r["exclusion_reasons"]]
        excluded_outlier_rows = []

        # time-weighted base metrics and outlier marking
        inc_values = [r["normalized_unit_price"] for r in included_rows]
        inc_weights = [r["weight"] for r in included_rows]
        stats = range_statistics(inc_values, inc_weights)

        # Detect outliers by IQR and move to excluded
        lower_bound, upper_bound = outlier_bounds([v for v in inc_values if v is not None])
        if lower_bound is not None and upper_bound is not None and included_rows:
            kept_rows = []
            for r in included_rows:
                price = r["normalized_unit_price"]
                if price is None:
                    r["exclusion_reasons"].append("invalid_normalized_unit_price")
                    excluded_rows.append(r)
                    continue
                if price < lower_bound:
                    r["exclusion_reasons"].append("price_outlier_low")
                    excluded_outlier_rows.append(r)
                    excluded_rows.append(r)
                elif price > upper_bound:
                    r["exclusion_reasons"].append("price_outlier_high")
                    excluded_outlier_rows.append(r)
                    excluded_rows.append(r)
                else:
                    kept_rows.append(r)
            included_rows = kept_rows
            inc_values = [r["normalized_unit_price"] for r in included_rows]
            inc_weights = [r["weight"] for r in included_rows]
            stats = range_statistics(inc_values, inc_weights)

        included_observation_count = len(included_rows)
        excluded_observation_count = len(excluded_rows)
        summary["excluded_observation_count"] += excluded_observation_count

        low_confidence_count = sum(
            1 for r in rows if "alias_low_confidence" in r["warnings"] or "low_confidence" in r["exclusion_reasons"]
        )
        review_required_count = sum(1 for r in rows if "requires_human_review" in r["exclusion_reasons"] or r["requires_human_review"])
        outlier_count = len(excluded_outlier_rows)

        observation_ids = [r["observation_id"] for r in rows]
        excluded_observation_ids = [r["observation_id"] for r in excluded_rows]

        warnings = []
        if included_observation_count < 2:
            warnings.append("insufficient_observation_count")
        if review_required_count > 0:
            warnings.append("source_observations_require_review")
        if excluded_observation_count > 0:
            warnings.append("has_excluded_observations")

        price_min = stats["price_min"]
        price_max = stats["price_max"]
        if price_min is not None and price_max is not None and price_min > 0:
            gap = price_max - price_min
            if gap > price_min * 3 or (gap > 500 and price_min < 100):
                warnings.append("price_span_too_large")

        if outlier_count > 0:
            warnings.append("outlier_observed")

        null_reasons = display_null_reasons(
            stats,
            included_observation_count,
            excluded_observation_count,
            observation_count,
            review_required_count,
        )
        warnings.extend(null_reasons)

        requires_review = bool(warnings) and (
            included_observation_count < 2 or review_required_count > 0 or excluded_observation_count > 0 or outlier_count > 0
        )

        price_range = {
            "price_range_id": build_price_range_id(group_key, seq),
            "id": build_price_range_id(group_key, seq),
            "canonical_item_code": canonical_item_code,
            "canonical_item_name": canonical_item_name,
            "unit_normalized": unit_normalized,
            "work_material_scope": work_material_scope,
            "region_normalized": region_normalized,
            "currency": currency,
            "group_key_summary": build_group_key_summary(group_key),
            "price_min": price_min,
            "price_max": price_max,
            "price_median": stats["price_median"],
            "price_weighted_avg": stats["price_weighted_avg"],
            "display_unit_price": stats["display_unit_price"],
            "display_null_reason_codes": null_reasons,
            "observation_count": observation_count,
            "included_observation_count": included_observation_count,
            "excluded_observation_count": excluded_observation_count,
            "low_confidence_count": low_confidence_count,
            "excluded_outlier_count": outlier_count,
            "review_required_count": review_required_count,
            "observation_ids": observation_ids,
            "excluded_observation_ids": excluded_observation_ids,
            "warnings": sorted(set(warnings)),
            "requires_human_review": requires_review,
            "created_at": now_ts(),
            "updated_at": now_ts(),
            "schema_version": SCHEMA_VERSION,
            "upload_stage": "staging_candidate",
            "source_file_ids": sorted(set(safe_str(obs.get("source_file_id")) for obs in observations if isinstance(obs, dict) and safe_str(obs.get("canonical_item_code")).strip() == canonical_item_code)),
        }

        price_ranges.append(price_range)
        summary["generated_price_range_count"] += 1

    units_by_canonical = defaultdict(set)
    for price_range in price_ranges:
        units_by_canonical[price_range["canonical_item_code"]].add(price_range["unit_normalized"])

    for price_range in price_ranges:
        units = units_by_canonical[price_range["canonical_item_code"]]
        if "M2" in units and "PING" in units:
            price_range["warnings"] = sorted(set(price_range.get("warnings", []) + ["cross_unit_review_required"]))
            price_range["requires_human_review"] = True

    review_queue = []
    for price_range in price_ranges:
        if (
            price_range["included_observation_count"] < 2
            or price_range["review_required_count"] > 0
            or "price_span_too_large" in price_range["warnings"]
            or price_range["excluded_observation_count"] > 0
            or "cross_unit_review_required" in price_range["warnings"]
        ):
            review_queue.append(
                {
                    "id": price_range["price_range_id"],
                    "price_range_id": price_range["price_range_id"],
                    "canonical_item_code": price_range["canonical_item_code"],
                    "canonical_item_name": price_range["canonical_item_name"],
                    "unit_normalized": price_range["unit_normalized"],
                    "work_material_scope": price_range["work_material_scope"],
                    "region_normalized": price_range["region_normalized"],
                    "currency": price_range["currency"],
                    "group_key_summary": price_range["group_key_summary"],
                    "display_null_reason_codes": price_range["display_null_reason_codes"],
                    "included_observation_count": price_range["included_observation_count"],
                    "excluded_observation_count": price_range["excluded_observation_count"],
                    "excluded_observation_ids": price_range["excluded_observation_ids"],
                    "requires_human_review": True,
                    "review_reason_codes": review_reasons_for_range(price_range),
                    "created_at": now_ts(),
                    "updated_at": now_ts(),
                    "schema_version": SCHEMA_VERSION,
                    "upload_stage": "review_required",
                }
            )
            summary["review_range_count"] += 1

    write_json(output_path, price_ranges)
    write_json(review_output_path, review_queue)

    summary["forbidden_field_hit_count"] = 1 if has_forbidden_fields(price_ranges, FORBIDDEN_FIELDS) else 0
    return summary, price_ranges, review_queue


def parse_args():
    parser = argparse.ArgumentParser(description="Generate PriceRange from PriceObservation samples.")
    parser.add_argument(
        "--input-dir",
        action="append",
        nargs="*",
        help="Input PriceObservation JSON paths; repeat or pass multiple paths in one option",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--review-output", default=str(DEFAULT_REVIEW_OUTPUT_PATH))
    return parser.parse_args()


def main():
    args = parse_args()
    flat_inputs = None
    if args.input_dir:
        flat_inputs = []
        for item in args.input_dir:
            flat_inputs.extend([Path(p) for p in item if isinstance(p, str)])
    summary, price_ranges, review_queue = run_generation(
        input_paths=[Path(p) for p in flat_inputs] if flat_inputs else None,
        output_path=Path(args.output),
        review_output_path=Path(args.review_output),
    )
    print("price range generation summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"input paths: {', '.join(str(p) for p in (flat_inputs or [str(p) for p in DEFAULT_OBSERVATION_PATHS]))}")
    print(f"output: {args.output} ({len(price_ranges)} ranges)")
    print(f"review output: {args.review_output} ({len(review_queue)} ranges)")


if __name__ == "__main__":
    main()
