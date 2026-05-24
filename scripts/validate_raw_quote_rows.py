import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT_DIR / "samples" / "sample_normalized_quote_rows.json"


REQUIRED_FIELDS = {
    "row_id",
    "source_file_id",
    "source_file_name",
    "source_type",
    "row_index",
    "row_role",
}

ALLOWED_ROLES = {
    "trade_category_header",
    "quote_line",
    "subtotal",
    "total",
    "note",
    "empty",
    "unknown",
}


def parse_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("，", "").replace("$", "").replace("NT$", "")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def is_missing_text(value):
    return value is None or str(value).strip() == ""


def almost_equal(amount, calc):
    if amount is None or calc is None:
        return True
    tolerance = max(1.0, abs(calc) * 0.01)
    return abs(amount - calc) <= tolerance


def main():
    if not INPUT_PATH.exists():
        print(f"input file not found: {INPUT_PATH}")
        return 1

    rows = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    total = len(rows)
    issue_counts = {
        "missing_required_field": 0,
        "invalid_row_role": 0,
        "quote_line_missing_item_name": 0,
        "blocked_row_present": 0,
        "amount_mismatch": 0,
        "invalid_amount_fields": 0,
    }
    invalid_rows = []

    blocked_rows = [r for r in rows if r.get("blocked") is True]
    for row in rows:
        row_id = row.get("row_id", "<missing_row_id>")
        row_issues = []

        for field in REQUIRED_FIELDS:
            if is_missing_text(row.get(field)):
                issue_counts["missing_required_field"] += 1
                row_issues.append(f"missing_required_field:{field}")

        role = row.get("row_role")
        if role not in ALLOWED_ROLES:
            issue_counts["invalid_row_role"] += 1
            row_issues.append(f"invalid_row_role:{role}")

        if role == "quote_line":
            if is_missing_text(row.get("item_name_raw")) and is_missing_text(row.get("item_name_normalized")):
                issue_counts["quote_line_missing_item_name"] += 1
                row_issues.append("quote_line_missing_item_name")

            quantity = parse_number(row.get("quantity_normalized"))
            unit_price = parse_number(row.get("unit_price_observed"))
            amount = parse_number(row.get("amount_observed"))
            if row.get("amount_raw") not in (None, "") and amount is None:
                issue_counts["invalid_amount_fields"] += 1
                row_issues.append("invalid_amount_observed")
            if quantity is not None and unit_price is not None and amount is not None:
                if not almost_equal(amount, quantity * unit_price):
                    issue_counts["amount_mismatch"] += 1
                    row_issues.append("amount_mismatch")

        if row.get("blocked") is True:
            issue_counts["blocked_row_present"] += 1

        if row_issues:
            invalid_rows.append({"row_id": row_id, "issues": row_issues})

    summary = {
        "input_row_count": total,
        "blocked_row_count": len(blocked_rows),
        "missing_required_field_count": issue_counts["missing_required_field"],
        "invalid_row_role_count": issue_counts["invalid_row_role"],
        "quote_line_missing_item_name_count": issue_counts["quote_line_missing_item_name"],
        "invalid_amount_field_count": issue_counts["invalid_amount_fields"],
        "amount_mismatch_count": issue_counts["amount_mismatch"],
        "invalid_rows": invalid_rows,
    }

    print("validation summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    failed = len(invalid_rows) > 0
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
