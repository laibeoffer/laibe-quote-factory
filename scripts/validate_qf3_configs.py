import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "configs"

REQUIRED_CONFIG_KEYS = {
    "header_aliases.json": [["item_name"], ["unit"], ["quantity"], ["unit_price"], ["amount"], ["note"]],
    "item_alias_dictionary.json": [["canonical_items"]],
    "unit_normalization_rules.json": [["unit_rules"]],
    "work_material_rules.json": [["default_region"], ["trade_defaults"], ["exceptions"]],
    "price_observation_schema.json": [["price_observation"]],
    "time_weight_rules.json": [["time_weights"], ["price_range_fields"]],
    "equipment_allowance_rules.json": [["tile"], ["bathroom_fixture"], ["lighting"]]
}


def validate_json(path: Path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return True, payload, None
    except Exception as exc:
        return False, None, str(exc)


def get_by_path(payload, path):
    cur = payload
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def validate_header_aliases(payload):
    errors = []
    expected = ["item_name", "unit", "quantity", "unit_price", "amount", "note"]
    for k in expected:
        if k not in payload or not isinstance(payload[k], list):
            errors.append(f"header_aliases missing list: {k}")
    return errors


def validate_item_alias(payload):
    errors = []
    items = payload.get("canonical_items")
    if not isinstance(items, list) or not items:
        errors.append("item_alias_dictionary missing canonical_items list")
        return errors
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"item_alias_dictionary[{idx}] must be object")
            continue
        code = item.get("canonical_item_code")
        aliases = item.get("aliases")
        if not code:
            errors.append(f"item_alias_dictionary[{idx}] missing canonical_item_code")
        if not isinstance(aliases, list) or len(aliases) == 0:
            errors.append(f"item_alias_dictionary[{idx}] missing aliases")
    return errors


def validate_unit_rules(payload):
    errors = []
    rules = payload.get("unit_rules")
    if not isinstance(rules, list) or not rules:
        return ["unit_normalization_rules missing unit_rules"]

    has_ping = False
    has_m2 = False
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        aliases = rule.get("aliases", [])
        norm = rule.get("normalized_unit")
        if "PING" in (norm,):
            has_ping = True
        if norm == "M2":
            has_m2 = True
        if not isinstance(aliases, list):
            errors.append("unit rule missing aliases list")

    if not has_ping or not has_m2:
        errors.append("unit rules missing conversion anchor for 坪 <-> M2")
    return errors


def validate_work_material(payload):
    errors = []
    if payload.get("default_region") != "Taipei":
        errors.append("work_material_rules default_region should be Taipei")

    for k in ["trade_defaults", "exceptions"]:
        if k not in payload:
            errors.append(f"work_material_rules missing {k}")
    return errors


def validate_time_weight(payload):
    errors = []
    weights = payload.get("time_weights", {})
    required_w = ["recent_0_12_months_weight", "months_12_24_weight", "months_24_36_weight"]
    for w in required_w:
        if w not in weights:
            errors.append(f"time_weight_rules missing {w}")
    return errors


def validate_schema(payload):
    errors = []
    po = payload.get("price_observation", {})
    if not isinstance(po, dict):
        errors.append("price_observation_schema missing price_observation object")
        return errors

    required_fields = [
        "observation_id",
        "source_file_id",
        "source_file_name",
        "quote_date",
        "observed_year",
        "region_normalized",
        "trade_category",
        "item_name_raw",
        "unit_raw",
        "unit_normalized",
        "conversion_factor",
        "currency",
        "work_material_scope",
        "warnings",
        "requires_human_review",
    ]
    for f in required_fields:
        if f not in po:
            errors.append(f"price_observation_schema missing {f}")
    return errors


def validate_equipment(payload):
    warnings = []
    required_blocks = ["tile", "bathroom_fixture", "lighting", "high_value_equipment"]
    for b in required_blocks:
        if b not in payload:
            warnings.append(f"equipment_allowance_rules missing {b}")
    return warnings


def count_exceptions(payload):
    exceptions = payload.get("exceptions", {})
    if not isinstance(exceptions, dict):
        return 0
    return sum(len(v) for v in exceptions.values() if isinstance(v, list))


def count_canonical_items(payload):
    items = payload.get("canonical_items", [])
    return len(items) if isinstance(items, list) else 0


def count_unit_rules(payload):
    rules = payload.get("unit_rules", [])
    return len(rules) if isinstance(rules, list) else 0


def main():
    all_files = sorted([p for p in CONFIG_DIR.glob("*.json") if p.is_file()])
    errors = []
    warnings = []
    valid_count = 0

    parsed = {}
    for p in all_files:
        ok, payload, err = validate_json(p)
        if not ok:
            errors.append(f"{p.name}: invalid json ({err})")
            continue
        valid_count += 1
        parsed[p.name] = payload

    for name, required_paths in REQUIRED_CONFIG_KEYS.items():
        payload = parsed.get(name)
        if payload is None:
            errors.append(f"missing config: {name}")
            continue
        for req in required_paths:
            if get_by_path(payload, req) is None:
                errors.append(f"{name} missing {'.'.join(req)}")

    if "header_aliases.json" in parsed:
        errors.extend(validate_header_aliases(parsed["header_aliases.json"]))
    if "item_alias_dictionary.json" in parsed:
        errors.extend(validate_item_alias(parsed["item_alias_dictionary.json"]))
    if "unit_normalization_rules.json" in parsed:
        errors.extend(validate_unit_rules(parsed["unit_normalization_rules.json"]))
    if "work_material_rules.json" in parsed:
        errors.extend(validate_work_material(parsed["work_material_rules.json"]))
    if "time_weight_rules.json" in parsed:
        errors.extend(validate_time_weight(parsed["time_weight_rules.json"]))
    if "price_observation_schema.json" in parsed:
        errors.extend(validate_schema(parsed["price_observation_schema.json"]))
    if "equipment_allowance_rules.json" in parsed:
        warnings.extend(validate_equipment(parsed["equipment_allowance_rules.json"]))

    canonical_item_count = count_canonical_items(parsed.get("item_alias_dictionary.json", {}))
    unit_rule_count = count_unit_rules(parsed.get("unit_normalization_rules.json", {}))
    work_material_exception_count = count_exceptions(parsed.get("work_material_rules.json", {}))

    summary = {
        "config_file_count": len(all_files),
        "valid_config_count": valid_count,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "canonical_item_count": canonical_item_count,
        "unit_rule_count": unit_rule_count,
        "work_material_exception_count": work_material_exception_count,
        "formal_price_generated": False,
        "formal_pricing_rule_generated": False,
        "budget_estimate_line_generated": False,
        "errors": errors,
        "warnings": warnings
    }

    print("qf3 config validation summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
