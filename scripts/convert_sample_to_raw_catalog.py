import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
INPUT_ROWS_PATH = ROOT_DIR / "samples" / "sample_normalized_quote_rows.json"
CONFIG_PATH = ROOT_DIR / "configs" / "raw_quote_to_catalog_mapping.json"
OUTPUT_SOURCE_PATH = ROOT_DIR / "exports_to_raw_warehouse" / "sample_raw_catalog_source.json"
OUTPUT_REVIEW_PATH = ROOT_DIR / "review_queue" / "sample_quote_row_review_queue.json"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_field(row, mapping_value):
    if isinstance(mapping_value, str):
        return row.get(mapping_value)
    if isinstance(mapping_value, dict):
        if "field" in mapping_value:
            candidate = row.get(mapping_value["field"])
            if (candidate is None or candidate == "") and "fallback" in mapping_value:
                return mapping_value.get("fallback")
            return candidate
        if "primary" in mapping_value and "fallback" in mapping_value:
            primary = row.get(mapping_value["primary"])
            if primary not in (None, ""):
                return primary
            return row.get(mapping_value["fallback"])
    return None


def parse_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = (
        str(value)
        .strip()
        .replace(",", "")
        .replace("，", "")
        .replace("$", "")
        .replace("NT$", "")
    )
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def build_metadata(row, metadata_fields):
    return {field: row.get(field) for field in metadata_fields}


def row_to_raw_item(row, mapping):
    item = {}
    for target, source in mapping["item_fields"].items():
        if target == "source_id":
            item[target] = row.get("source_file_id")
        elif target == "raw_text":
            continue
        else:
            item[target] = get_field(row, source)

    item["raw_text"] = " / ".join(
        filter(
            None,
            [
                row.get("trade_category_raw", ""),
                row.get("item_name_raw", ""),
                row.get("unit_raw", ""),
                row.get("note_raw", ""),
            ],
        )
    )
    item["metadata"] = build_metadata(row, mapping["metadata_fields"])
    return item


def build_source(rows, mapping):
    source_row = rows[0] if rows else {}
    source = {
        "id": get_field(source_row, mapping["source_fields"]["id"]),
        "source_type": get_field(source_row, mapping["source_fields"]["source_type"]),
        "source_name": get_field(source_row, mapping["source_fields"]["source_name"]),
        "source_date": get_field(source_row, mapping["source_fields"]["source_date"]),
        "source_note": get_field(source_row, mapping["source_fields"]["source_note"]),
        "region": mapping["source_fields"]["region"],
        "currency": get_field(source_row, mapping["source_fields"]["currency"]),
        "source_reliability": mapping["source_fields"]["source_reliability"],
        "raw_items": [],
    }
    if source["currency"] in (None, ""):
        source["currency"] = "TWD"
    return source


def is_amount_mismatch(row):
    quantity = parse_float(row.get("quantity_normalized"))
    unit_price = parse_float(row.get("unit_price_observed"))
    amount = parse_float(row.get("amount_observed"))
    if quantity is None or unit_price is None or amount is None:
        return False
    expected = quantity * unit_price
    tolerance = max(1.0, abs(expected) * 0.01)
    return abs(amount - expected) > tolerance


def should_export(row, allowed_roles):
    return row.get("row_role") in allowed_roles and row.get("blocked") is not True


def should_review(row, mapping):
    if mapping["review_conditions"]["include_if_human_review"] and row.get("requires_human_review") is True:
        return True
    if mapping["review_conditions"]["include_if_warnings"]:
        parse_warnings = row.get("parse_warnings")
        return bool(parse_warnings)
    return False


def main():
    rows = read_json(INPUT_ROWS_PATH)
    mapping = read_json(CONFIG_PATH)
    allowed_roles = set(mapping["conversion_conditions"]["allowed_roles"])

    source = build_source(rows, mapping)
    raw_items = []
    review_rows = []
    amount_mismatch_count = 0
    skipped_row_count = 0
    blocked_row_count = 0

    for row in rows:
        if row.get("blocked") is True:
            blocked_row_count += 1
            if should_review(row, mapping):
                review_rows.append(row)
            continue

        if should_export(row, allowed_roles):
            if is_amount_mismatch(row):
                amount_mismatch_count += 1
            raw_items.append(row_to_raw_item(row, mapping))
        else:
            skipped_row_count += 1

        if should_review(row, mapping):
            review_rows.append(row)

    source["raw_items"] = raw_items

    save_json(OUTPUT_SOURCE_PATH, source)
    save_json(OUTPUT_REVIEW_PATH, review_rows)

    summary = {
        "input_row_count": len(rows),
        "exported_raw_item_count": len(raw_items),
        "skipped_row_count": skipped_row_count,
        "review_queue_count": len(review_rows),
        "blocked_row_count": blocked_row_count,
        "amount_mismatch_count": amount_mismatch_count,
        "formal_price_generated": False,
        "formal_pricing_rule_generated": False,
        "budget_estimate_line_generated": False,
    }

    print("convert summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
