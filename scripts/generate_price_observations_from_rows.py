import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
ITEM_ALIAS_CONFIG_PATH = ROOT_DIR / "configs" / "item_alias_dictionary.json"
UNIT_RULE_CONFIG_PATH = ROOT_DIR / "configs" / "unit_normalization_rules.json"
WORK_MATERIAL_CONFIG_PATH = ROOT_DIR / "configs" / "work_material_rules.json"
PRICE_OBSERVATION_SCHEMA_PATH = ROOT_DIR / "configs" / "price_observation_schema.json"
TIME_WEIGHT_CONFIG_PATH = ROOT_DIR / "configs" / "time_weight_rules.json"
EQUIPMENT_RULE_CONFIG_PATH = ROOT_DIR / "configs" / "equipment_allowance_rules.json"

DEFAULT_INPUT_PATH = ROOT_DIR / "samples" / "sample_normalized_quote_rows.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_observations.json"
DEFAULT_REVIEW_OUTPUT_PATH = ROOT_DIR / "review_queue" / "sample_price_observation_review_queue.json"

SCHEMA_VERSION = "qf3_v1"
ALLOWED_UPLOAD_STAGES = {
    "local_only",
    "staging_candidate",
    "review_required",
    "approved_for_cloud",
    "archived",
}
FORBIDDEN_FIELDS = {
    "unit_price",
    "formal_price",
    "approved_price",
    "pricing_rule_id",
    "budget_estimate_line_id",
}
KNOWN_WORK_SCOPE = {
    "labor_only",
    "material_only",
    "labor_and_material",
    "equipment_allowance",
    "unknown",
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
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text == "":
        return None
    text = re.sub(r"[T$NT\$]+", "", text)
    text = text.replace("NT", "").replace("元", "").replace(" ", "")
    try:
        return float(text)
    except ValueError:
        return None


def safe_str(value):
    return "" if value is None else str(value)


def normalize_text(value):
    return safe_str(value).strip().lower()


def normalize_unit_rules(rule_config):
    rule_map = {}
    for rule in rule_config.get("unit_rules", []):
        aliases = rule.get("aliases", [])
        for alias in aliases:
            if isinstance(alias, str):
                rule_map[safe_str(alias).strip().lower()] = rule
    return rule_map


def match_unit(unit_raw, rule_map, fallback_conversion_factor=1.0):
    unit_text = safe_str(unit_raw).strip()
    if unit_text == "":
        return {
            "unit_raw": unit_text,
            "unit_normalized": "UNKNOWN",
            "conversion_factor": fallback_conversion_factor,
            "requires_human_review": True,
            "warning": "unit_unrecognized",
        }
    rule = rule_map.get(unit_text.strip().lower())
    if rule is None:
        return {
            "unit_raw": unit_text,
            "unit_normalized": "UNKNOWN",
            "conversion_factor": fallback_conversion_factor,
            "requires_human_review": True,
            "warning": "unit_unrecognized",
        }
    return {
        "unit_raw": unit_text,
        "unit_normalized": rule.get("normalized_unit", "UNKNOWN"),
        "conversion_factor": to_num(rule.get("conversion_factor")) or fallback_conversion_factor,
        "conversion_direction": rule.get("conversion_direction", "count_unit"),
        "requires_human_review": False,
        "warning": None,
    }


def build_trade_defaults(work_config):
    trade_map = {}
    for item in work_config.get("trade_defaults", []):
        trade_map[safe_str(item.get("trade_category")).strip().lower()] = item.get("work_material_scope", "unknown")
    return trade_map


def build_exceptions_map(work_config):
    raw = work_config.get("exceptions", {})
    mapped = {}
    for trade_key, entries in raw.items():
        mapped[safe_str(trade_key).strip().lower()] = []
        for entry in entries:
            if isinstance(entry, dict):
                keyword = safe_str(entry.get("keyword")).strip().lower()
                if keyword:
                    mapped[safe_str(trade_key).strip().lower()].append(
                        (
                            keyword,
                            safe_str(entry.get("work_material_scope", "unknown")).strip().lower(),
                        )
                    )
    return mapped


def match_work_material_scope(row, trade_map, exceptions_map):
    trade = normalize_text(row.get("trade_category_normalized") or row.get("trade_category_raw") or "")
    item_text = normalize_text(" ".join(filter(None, [
        safe_str(row.get("item_name_normalized")),
        safe_str(row.get("item_name_raw")),
        safe_str(row.get("spec_normalized")),
        safe_str(row.get("spec_raw")),
        safe_str(row.get("note_normalized")),
        safe_str(row.get("note_raw")),
    ])))

    scope = trade_map.get(trade, "unknown")
    reason = "trade_default"

    for key, scoped_rules in exceptions_map.items():
        if key != trade:
            continue
        for keyword, candidate_scope in scoped_rules:
            if keyword and keyword in item_text:
                scope = candidate_scope
                reason = f"exception:{keyword}"
                break

    if scope == "material_only_or_review":
        scope = "material_only"
    if scope not in KNOWN_WORK_SCOPE:
        return "unknown", reason
    if scope == "unknown" and not trade:
        return "unknown", "missing_trade_category"
    return scope, reason


def normalize_unit_price(observed_unit_price, unit_meta):
    observed = to_num(observed_unit_price)
    factor = to_num(unit_meta.get("conversion_factor"))
    if observed is None:
        return None
    if factor is None:
        return observed
    return observed * factor


def quote_year(quote_date):
    text = safe_str(quote_date).strip()
    if not text:
        return None
    if len(text) >= 4 and text[0:4].isdigit():
        try:
            return int(text[0:4])
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text).year
    except Exception:
        return None


def alias_score_for_row(row, canonical_item, trade_value):
    item_name = normalize_text(row.get("item_name_normalized") or row.get("item_name_raw") or "")
    spec = normalize_text(row.get("spec_normalized") or row.get("spec_raw") or "")
    note = normalize_text(row.get("note_normalized") or row.get("note_raw") or "")
    target = " ".join(part for part in [item_name, spec, note] if part)

    aliases = [normalize_text(a) for a in canonical_item.get("aliases", [])]
    matched_aliases = [alias for alias in aliases if alias and alias in target]
    if not matched_aliases:
        return 0.0, [], []

    positive_terms = [normalize_text(t) for t in canonical_item.get("positive_context_terms", [])]
    negative_terms = [normalize_text(t) for t in canonical_item.get("negative_context_terms", [])]

    positive_hits = [term for term in positive_terms if term and term in target]
    negative_hits = [term for term in negative_terms if term and term in target]

    score = 0.8
    score += min(0.15, 0.05 * len(positive_hits))
    score -= 0.3 * len(negative_hits)

    if trade_value and normalize_text(canonical_item.get("trade_category")) == trade_value:
        score += 0.05

    return score, positive_hits, negative_hits


def match_canonical(row, canonical_config, default_requires_review=False):
    trade = normalize_text(row.get("trade_category_normalized") or row.get("trade_category_raw") or "")
    item_name = normalize_text(row.get("item_name_normalized") or row.get("item_name_raw") or "")
    spec = normalize_text(row.get("spec_normalized") or row.get("spec_raw") or "")
    note = normalize_text(row.get("note_normalized") or row.get("note_raw") or "")
    target = " ".join(part for part in [item_name, spec, note] if part)

    if not target:
        return (
            None,
            None,
            {
                "alias_score": 0.0,
                "alias_hits": [],
                "positive_hits": [],
                "negative_hits": [],
                "auto_matched": False,
            },
            True,
            ["alias_unmatched_or_unsafe"],
        )

    best = None
    best_score = -1.0
    best_alias_hits = []

    for item in canonical_config.get("canonical_items", []):
        aliases = [normalize_text(a) for a in item.get("aliases", [])]
        if not any(alias and alias in target for alias in aliases):
            continue

        score, positive_hits, negative_hits = alias_score_for_row(row, item, trade)

        matched_aliases = [alias for alias in aliases if alias and alias in target]
        if not matched_aliases:
            continue

        if score > best_score:
            best_score = score
            best = item
            best_alias_hits = matched_aliases
            best_positive = positive_hits
            best_negative = negative_hits

    if best is None:
        return (
            None,
            None,
            {
                "alias_score": 0.0,
                "alias_hits": [],
                "positive_hits": [],
                "negative_hits": [],
                "auto_matched": False,
            },
            True,
            ["alias_unmatched_or_unsafe"],
        )

    warnings = []
    auto_matched = False
    canonical_item_code = best.get("canonical_item_code")
    canonical_item_name = best.get("canonical_item_name")

    _, best_positive_hits, best_negative_hits = alias_score_for_row(row, best, trade)
    # recompute to keep same logic with final matched row
    score, _, negative_hits = alias_score_for_row(row, best, trade)
    has_negative = len(negative_hits) > 0
    if has_negative:
        warnings.append("alias_negative_context_hit")
        requires_human_review = True
        # Keep candidate for review when alias still appears; avoid unsafe auto match
        auto_matched = False
    elif score >= 0.9:
        auto_matched = True
        requires_human_review = False
    elif 0.75 <= score < 0.9:
        warnings.append("alias_low_confidence")
        requires_human_review = True
    else:
        canonical_item_code = None
        canonical_item_name = None
        warnings.append("alias_unmatched_or_unsafe")
        requires_human_review = True

    if default_requires_review:
        requires_human_review = True

    metadata = {
        "alias_score": score,
        "alias_hits": best_alias_hits,
        "positive_hits": best_positive_hits,
        "negative_hits": best_negative_hits,
        "auto_matched": auto_matched,
    }
    return canonical_item_code, canonical_item_name, metadata, requires_human_review, warnings


def to_warning_list(row):
    warnings = []
    for value in row.get("parse_warnings") or []:
        if isinstance(value, str):
            warnings.append(value)
    return warnings


def to_review_payload(observation, review_reasons):
    return {
        "id": observation.get("observation_id"),
        "observation_id": observation.get("observation_id"),
        "source_file_id": observation.get("source_file_id"),
        "source_row_id": observation.get("source_row_id"),
        "source_file_name": observation.get("source_file_name"),
        "source_type": observation.get("source_type"),
        "quote_date": observation.get("quote_date"),
        "trade_category": observation.get("trade_category"),
        "canonical_item_code": observation.get("canonical_item_code"),
        "item_name_raw": observation.get("item_name_raw"),
        "observed_unit_price": observation.get("observed_unit_price"),
        "normalized_unit_price": observation.get("normalized_unit_price"),
        "unit_raw": observation.get("unit_raw"),
        "unit_normalized": observation.get("unit_normalized"),
        "requires_human_review": observation.get("requires_human_review"),
        "upload_stage": "review_required",
        "review_status": "required",
        "review_reason_codes": review_reasons,
        "created_at": observation.get("created_at"),
        "updated_at": observation.get("updated_at"),
        "schema_version": observation.get("schema_version"),
    }


def map_row_to_observation(row, config):
    row_id = row.get("row_id")
    unit_lookup = config["unit_lookup"]
    canonical_config = config["canonical_config"]
    trade_map = config["trade_map"]
    exceptions_map = config["exceptions_map"]
    default_region = config["default_region"]

    unit_meta = match_unit(row.get("unit_raw"), unit_lookup)
    unit_unknown = unit_meta.get("unit_normalized") == "UNKNOWN"
    unit_warnings = []
    if unit_unknown:
        unit_warnings.append("unit_unrecognized")

    warnings = to_warning_list(row) + unit_warnings
    trade_value = normalize_text(
        row.get("trade_category_normalized") or row.get("trade_category_raw") or ""
    )

    canonical_item_code, canonical_item_name, alias_meta, requires_review_canonical, canonical_warnings = match_canonical(
        row,
        canonical_config,
        default_requires_review=bool(row.get("requires_human_review")),
    )
    warnings += canonical_warnings

    requires_review = bool(row.get("requires_human_review")) or bool(unit_unknown) or bool(requires_review_canonical)

    scope, scope_reason = match_work_material_scope(row, trade_map, exceptions_map)
    if scope == "unknown":
        requires_review = True
        if "work_material_unknown" not in warnings:
            warnings.append("work_material_unknown")

    item_text = normalize_text(
        " ".join(
            filter(
                None,
                [
                    safe_str(row.get("item_name_normalized")),
                    safe_str(row.get("item_name_raw")),
                    safe_str(row.get("spec_normalized")),
                    safe_str(row.get("spec_raw")),
                    safe_str(row.get("note_normalized")),
                    safe_str(row.get("note_raw")),
                ],
            )
        )
    )

    method_tags = []
    spec_tags = []
    if any(t in item_text for t in ["照明", "燈具", "崁燈", "軌道燈", "吊燈", "主燈"]):
        method_tags.append("lighting")
        spec_tags.append("lighting")
    if "機器" in item_text:
        method_tags.append("equipment")
        spec_tags.append("equipment")
    if "高價" in item_text and "五金" in item_text:
        scope = "equipment_allowance"
        if "高價五金" not in spec_tags:
            spec_tags.append("high_value_hardware")
        warnings.append("high_value_hardware")
        requires_review = True

    if scope == "equipment_allowance" and "equipment_allowance" not in spec_tags:
        spec_tags.append("equipment_allowance")

    observed_unit_price = to_num(row.get("unit_price_observed"))
    amount_observed = to_num(row.get("amount_observed"))
    normalized_price = normalize_unit_price(observed_unit_price, unit_meta)

    quote_date = safe_str(row.get("quote_date"))
    obs = {
        "observation_id": f"{row_id}-obs",
        "id": f"{row_id}-obs",
        "source_file_id": row.get("source_file_id"),
        "source_row_id": row_id,
        "source_file_name": row.get("source_file_name"),
        "quote_date": quote_date if quote_date else None,
        "observed_year": quote_year(quote_date),
        "region_raw": row.get("region", ""),
        "region_normalized": default_region or "Taipei",
        "trade_category": row.get("trade_category_normalized") or row.get("trade_category_raw") or "",
        "canonical_item_code": canonical_item_code,
        "canonical_item_name": canonical_item_name,
        "item_name_raw": row.get("item_name_raw"),
        "item_name_normalized": row.get("item_name_normalized"),
        "brand": row.get("brand_raw") or row.get("brand_normalized"),
        "model": row.get("model_raw") or row.get("model_normalized"),
        "spec": row.get("spec_raw") or row.get("spec_normalized"),
        "method_tags": method_tags,
        "spec_tags": spec_tags,
        "work_material_scope": scope,
        "unit_raw": unit_meta.get("unit_raw"),
        "unit_normalized": unit_meta.get("unit_normalized"),
        "conversion_factor": unit_meta.get("conversion_factor", 1.0),
        "observed_unit_price": observed_unit_price,
        "normalized_unit_price": normalized_price,
        "amount_observed": amount_observed,
        "currency": row.get("currency_normalized") or "TWD",
        "confidence": row.get("confidence"),
        "warnings": sorted(set(warnings)),
        "requires_human_review": bool(requires_review),
        "created_at": now_ts(),
        "updated_at": now_ts(),
        "schema_version": SCHEMA_VERSION,
        "upload_stage": "review_required" if requires_review else "staging_candidate",
        "source_type": row.get("source_type"),
        "scope_applied_by": scope_reason,
    }

    if alias_meta is not None:
        obs["alias_meta"] = alias_meta

    return obs


def filter_rows(rows):
    for row in rows:
        if row.get("row_role") != "quote_line":
            continue
        if row.get("blocked"):
            continue
        yield row


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


def build_summary():
    return {
        "input_row_count": 0,
        "quote_line_count": 0,
        "generated_observation_count": 0,
        "review_queue_count": 0,
        "canonical_matched_count": 0,
        "canonical_unmatched_count": 0,
        "unit_normalized_count": 0,
        "unit_unknown_count": 0,
        "labor_only_count": 0,
        "labor_and_material_count": 0,
        "equipment_allowance_count": 0,
        "unknown_scope_count": 0,
        "low_confidence_count": 0,
        "auto_matched_count": 0,
        "alias_negative_context_count": 0,
        "alias_unmatched_count": 0,
        "forbidden_field_hit_count": 0,
        "formal_price_generated": False,
        "formal_pricing_rule_generated": False,
        "budget_estimate_line_generated": False,
    }


def add_scope_count(summary, scope):
    if scope == "labor_only":
        summary["labor_only_count"] += 1
    elif scope == "labor_and_material":
        summary["labor_and_material_count"] += 1
    elif scope == "equipment_allowance":
        summary["equipment_allowance_count"] += 1
    elif scope == "unknown":
        summary["unknown_scope_count"] += 1


def classify_warning_counts(summary, warnings):
    if "alias_low_confidence" in warnings:
        summary["low_confidence_count"] += 1
    if "alias_negative_context_hit" in warnings:
        summary["alias_negative_context_count"] += 1
    if "alias_unmatched_or_unsafe" in warnings:
        summary["alias_unmatched_count"] += 1


def to_counter(observations):
    return Counter([o.get("work_material_scope", "unknown") for o in observations])


def run_generation(input_path: Path, output_path: Path, review_output_path: Path):
    rows = load_json(input_path)
    canonical_config = load_json(ITEM_ALIAS_CONFIG_PATH)
    unit_config = load_json(UNIT_RULE_CONFIG_PATH)
    work_config = load_json(WORK_MATERIAL_CONFIG_PATH)
    load_json(PRICE_OBSERVATION_SCHEMA_PATH)
    load_json(TIME_WEIGHT_CONFIG_PATH)
    load_json(EQUIPMENT_RULE_CONFIG_PATH)

    unit_lookup = normalize_unit_rules(unit_config)
    trade_map = build_trade_defaults(work_config)
    exceptions_map = build_exceptions_map(work_config)
    default_region = work_config.get("default_region", "Taipei")

    config = {
        "canonical_config": canonical_config,
        "unit_lookup": unit_lookup,
        "trade_map": trade_map,
        "exceptions_map": exceptions_map,
        "default_region": default_region,
    }

    summary = build_summary()
    summary["input_row_count"] = len(rows)

    observations = []
    review_queue = []

    for row in filter_rows(rows):
        summary["quote_line_count"] += 1
        obs = map_row_to_observation(row, config)
        summary["generated_observation_count"] += 1

        if obs["canonical_item_code"]:
            summary["canonical_matched_count"] += 1
            if obs.get("alias_meta", {}).get("auto_matched", False):
                summary["auto_matched_count"] += 1
        else:
            summary["canonical_unmatched_count"] += 1

        if obs["unit_normalized"] != "UNKNOWN":
            summary["unit_normalized_count"] += 1
        else:
            summary["unit_unknown_count"] += 1

        add_scope_count(summary, obs["work_material_scope"])
        classify_warning_counts(summary, obs["warnings"])

        observations.append(obs)
        if obs["requires_human_review"] or bool(obs.get("warnings")):
            review_reasons = []
            if obs.get("canonical_item_code") is None:
                review_reasons.append("canonical_item_unmatched")
            if obs.get("requires_human_review"):
                review_reasons.append("requires_human_review")
            if obs.get("unit_normalized") == "UNKNOWN":
                review_reasons.append("unit_unknown")
            if obs.get("work_material_scope") == "unknown":
                review_reasons.append("work_material_unknown")
            if obs.get("canonical_item_code") is None and "alias_negative_context_hit" in obs.get("warnings", []):
                review_reasons.append("alias_negative_context")

            if "alias_low_confidence" in obs.get("warnings", []):
                review_reasons.append("alias_low_confidence")
            if "alias_negative_context_hit" in obs.get("warnings", []):
                review_reasons.append("alias_negative_context_hit")
            if "alias_unmatched_or_unsafe" in obs.get("warnings", []):
                review_reasons.append("alias_unmatched_or_unsafe")

            review = to_review_payload(obs, sorted(set(review_reasons)))
            review_queue.append(review)
            summary["review_queue_count"] += 1

    write_json(output_path, observations)
    write_json(review_output_path, review_queue)

    scope_count = to_counter(observations)
    summary["labor_only_count"] = scope_count.get("labor_only", 0)
    summary["labor_and_material_count"] = scope_count.get("labor_and_material", 0)
    summary["equipment_allowance_count"] = scope_count.get("equipment_allowance", 0)
    summary["unknown_scope_count"] = scope_count.get("unknown", 0)

    summary["forbidden_field_hit_count"] = 1 if has_forbidden_fields(observations, FORBIDDEN_FIELDS) else 0
    return summary, observations, review_queue


def parse_args():
    parser = argparse.ArgumentParser(description="Generate PriceObservation from RawQuoteRow sample.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Input RawQuoteRow JSON path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output PriceObservation JSON path")
    parser.add_argument(
        "--review-output",
        default=str(DEFAULT_REVIEW_OUTPUT_PATH),
        help="Output review queue JSON path",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    review_output_path = Path(args.review_output)

    summary, observations, review_queue = run_generation(input_path, output_path, review_output_path)
    print("price observation generation summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"input: {input_path}")
    print(f"output: {output_path} ({len(observations)} observations)")
    print(f"review output: {review_output_path} ({len(review_queue)} rows)")


if __name__ == "__main__":
    main()
