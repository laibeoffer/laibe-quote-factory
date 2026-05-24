import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

MAPPING_PATH = ROOT_DIR / "configs" / "cloud_table_mapping.json"

PAYLOAD_PATHS = {
    "sample_raw_catalog_source.json": ROOT_DIR / "exports_to_raw_warehouse" / "sample_raw_catalog_source.json",
    "sample_quote_row_review_queue.json": ROOT_DIR / "review_queue" / "sample_quote_row_review_queue.json",
    "sample_price_observations.json": ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_observations.json",
    "sample_price_observation_review_queue.json": ROOT_DIR / "review_queue" / "sample_price_observation_review_queue.json",
    "sample_alias_edge_case_price_observations.json": ROOT_DIR / "exports_to_raw_warehouse" / "sample_alias_edge_case_price_observations.json",
    "sample_alias_edge_case_review_queue.json": ROOT_DIR / "review_queue" / "sample_alias_edge_case_review_queue.json",
    "sample_alias_negative_context_price_observations.json": ROOT_DIR / "exports_to_raw_warehouse" / "sample_alias_negative_context_price_observations.json",
    "sample_alias_negative_context_review_queue.json": ROOT_DIR / "review_queue" / "sample_alias_negative_context_review_queue.json",
    "sample_price_ranges.json": ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_ranges.json",
    "sample_price_range_review_queue.json": ROOT_DIR / "review_queue" / "sample_price_range_review_queue.json",
    "sample_price_range_review_decisions.json": ROOT_DIR / "review_queue" / "sample_price_range_review_decisions.json",
    "sample_price_ranges_reviewed.json": ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_ranges_reviewed.json",
    "sample_price_range_review_overrides.json": ROOT_DIR / "review_queue" / "sample_price_range_review_overrides.json",
    "sample_price_ranges_reviewed_with_audit.json": ROOT_DIR / "exports_to_raw_warehouse" / "sample_price_ranges_reviewed_with_audit.json",
    "sample_price_range_review_audit_log.json": ROOT_DIR / "review_queue" / "sample_price_range_review_audit_log.json",
}

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

REQUIRED_TOP_FIELDS = [
    "id",
    "created_at",
    "updated_at",
    "schema_version",
    "upload_stage",
    "source_file_id",
]

REQUIRED_ROW_FIELDS = [
    "id",
    "source_file_id",
    "source_row_id",
    "upload_stage",
    "schema_version",
]

PRICE_OBSERVATION_REQUIRED_NONEMPTY = [
    "source_file_id",
    "source_row_id",
    "created_at",
    "updated_at",
    "schema_version",
    "upload_stage",
    "unit_raw",
    "unit_normalized",
    "requires_human_review",
]
PRICE_OBSERVATION_REQUIRED_KEY_ONLY = [
    "canonical_item_code",
    "observation_id",
    "id",
    "observed_unit_price",
    "normalized_unit_price",
    "unit_raw",
    "unit_normalized",
]
PRICE_RANGE_REQUIRED_NONEMPTY = [
    "created_at",
    "updated_at",
    "schema_version",
    "upload_stage",
    "canonical_item_code",
    "unit_normalized",
    "work_material_scope",
    "region_normalized",
    "currency",
    "group_key_summary",
    "price_min",
    "price_max",
    "price_median",
    "price_weighted_avg",
    "display_unit_price",
    "observation_count",
]
PRICE_RANGE_DECISION_REQUIRED_NONEMPTY = [
    "decision_id",
    "price_range_id",
    "reviewer_id",
    "decision",
    "suggested_decision",
    "decision_reason_codes",
    "reviewer_note",
    "decided_at",
    "source_observation_ids",
    "excluded_observation_ids",
    "upload_stage",
    "schema_version",
]
PRICE_RANGE_DECISIONS = {
    "approved_for_cloud",
    "rejected",
    "needs_more_observations",
    "needs_unit_review",
    "needs_scope_review",
    "needs_alias_review",
    "keep_as_historical_reference",
}
PRICE_RANGE_OVERRIDE_REQUIRED_NONEMPTY = [
    "override_id",
    "price_range_id",
    "previous_decision",
    "requested_decision",
    "reviewer_id",
    "override_reason_codes",
    "reviewer_note",
    "requested_at",
    "schema_version",
]
PRICE_RANGE_REVIEWED_WITH_AUDIT_REQUIRED_NONEMPTY = [
    "created_at",
    "updated_at",
    "schema_version",
    "upload_stage",
    "canonical_item_code",
    "unit_normalized",
    "work_material_scope",
    "region_normalized",
    "currency",
    "group_key_summary",
    "review_decision",
    "suggested_decision",
    "previous_decision",
    "final_decision",
    "reviewer_id",
    "reviewed_at",
    "decision_history",
]
PRICE_RANGE_AUDIT_LOG_REQUIRED_NONEMPTY = [
    "audit_event_id",
    "price_range_id",
    "event_type",
    "previous_decision",
    "requested_decision",
    "final_decision",
    "override_reason_codes",
    "reviewer_id",
    "reviewer_note",
    "event_time",
    "errors",
    "warnings",
    "schema_version",
]
PRICE_RANGE_AUDIT_EVENT_TYPES = {
    "override_requested",
    "override_applied",
    "override_rejected",
    "decision_preserved",
}


def read_json(path: Path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return True, payload, None
    except Exception as exc:
        return False, None, str(exc)


def add_error(summary, errors, message):
    summary["error_count"] += 1
    errors.append(message)


def check_upload_stage(obj, label, summary, errors):
    stage = obj.get("upload_stage")
    if stage not in ALLOWED_UPLOAD_STAGES:
        summary["upload_stage_invalid_count"] += 1
        summary["error_count"] += 1
        add_error(summary, errors, f"{label} upload_stage invalid: {stage}")
        return False
    return True


def check_required_nonempty(obj, required_fields, label, summary, errors):
    missing = []
    for field in required_fields:
        if obj.get(field) is None:
            missing.append(field)
    if missing:
        summary["missing_required_field_count"] += 1
        summary["error_count"] += 1
        add_error(summary, errors, f"{label} missing required fields: {', '.join(missing)}")
        return False
    return True


def check_required_keys(obj, required_fields, label, summary, errors):
    missing = []
    for field in required_fields:
        if field not in obj:
            missing.append(field)
    if missing:
        summary["missing_required_field_count"] += 1
        summary["error_count"] += 1
        add_error(summary, errors, f"{label} missing required keys: {', '.join(missing)}")
        return False
    return True


def check_has_keys(obj, required_keys, label, summary, errors):
    missing = [key for key in required_keys if key not in obj]
    if missing:
        summary["missing_required_field_count"] += 1
        summary["error_count"] += 1
        add_error(summary, errors, f"{label} missing required keys: {', '.join(missing)}")
        return False
    return True


def scan_forbidden_fields(obj, prefix, summary, warnings):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_FIELDS:
                summary["forbidden_field_hit_count"] += 1
                warnings.append(f"{prefix}.{key} is forbidden field")
            scan_forbidden_fields(value, f"{prefix}.{key}", summary, warnings)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            scan_forbidden_fields(item, f"{prefix}[{idx}]", summary, warnings)


def validate_source_payload(payload, summary, errors, warnings):
    valid_count = 0
    summary["checked_object_count"] += 1
    if not isinstance(payload, dict):
        add_error(summary, errors, "sample_raw_catalog_source.json must be object")
        return valid_count

    label = "sample_raw_catalog_source.json"
    if check_required_nonempty(payload, REQUIRED_TOP_FIELDS, label, summary, errors):
        valid_count += 1
    check_upload_stage(payload, label, summary, errors)

    if not isinstance(payload.get("raw_items"), list):
        add_error(summary, errors, "sample_raw_catalog_source.raw_items must be array")
        return valid_count

    for i, item in enumerate(payload.get("raw_items", [])):
        summary["checked_object_count"] += 1
        row_label = f"sample_raw_catalog_source.raw_items[{i}]"
        if not isinstance(item, dict):
            add_error(summary, errors, f"{row_label} is not object")
            continue
        if check_required_nonempty(item, REQUIRED_ROW_FIELDS, row_label, summary, errors):
            valid_count += 1
        check_upload_stage(item, row_label, summary, errors)
        if item.get("schema_version") in (None, ""):
            summary["missing_required_field_count"] += 1
            add_error(summary, errors, f"{row_label} has empty schema_version")
    scan_forbidden_fields(payload, "sample_raw_catalog_source", summary, warnings)
    return valid_count


def validate_review_payload(payload, payload_name, summary, errors, warnings, extra_required=None, key_only_extra=None):
    valid_count = 0
    summary["checked_object_count"] += 1
    if not isinstance(payload, list):
        add_error(summary, errors, f"{payload_name} must be array")
        return valid_count

    for i, item in enumerate(payload):
        summary["checked_object_count"] += 1
        row_label = f"{payload_name}[{i}]"
        if not isinstance(item, dict):
            add_error(summary, errors, f"{row_label} is not object")
            continue

        if check_required_nonempty(item, REQUIRED_ROW_FIELDS, row_label, summary, errors):
            valid_count += 1
        if check_upload_stage(item, row_label, summary, errors) and item.get("schema_version") in (None, ""):
            summary["missing_required_field_count"] += 1
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} has empty schema_version")
        if extra_required:
            check_required_nonempty(item, extra_required, row_label, summary, errors)
        if key_only_extra:
            check_has_keys(item, key_only_extra, row_label, summary, errors)
    scan_forbidden_fields(payload, payload_name, summary, warnings)
    return valid_count


def validate_observation_payload(payload, payload_name, summary, errors, warnings):
    valid_count = 0
    summary["checked_object_count"] += 1
    if not isinstance(payload, list):
        add_error(summary, errors, f"{payload_name} must be array")
        return valid_count

    for i, item in enumerate(payload):
        summary["checked_object_count"] += 1
        row_label = f"{payload_name}[{i}]"
        if not isinstance(item, dict):
            add_error(summary, errors, f"{row_label} is not object")
            continue

        if check_required_nonempty(item, PRICE_OBSERVATION_REQUIRED_NONEMPTY, row_label, summary, errors):
            valid_count += 1
        check_one_of_observation_id(item, row_label, summary, errors)
        check_has_keys(
            item,
            [k for k in PRICE_OBSERVATION_REQUIRED_KEY_ONLY if k != "observation_id"],
            row_label,
            summary,
            errors,
        )
        check_upload_stage(item, row_label, summary, errors)
        if item.get("schema_version") in (None, ""):
            summary["missing_required_field_count"] += 1
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} has empty schema_version")
    scan_forbidden_fields(payload, payload_name, summary, warnings)
    return valid_count


def check_has_keys_any(obj, keys, label, summary, errors):
    if any(key in obj for key in keys):
        return True
    summary["missing_required_field_count"] += 1
    summary["error_count"] += 1
    add_error(summary, errors, f"{label} missing required id key (id or price_range_id)")
    return False


def validate_price_range_payload(payload, payload_name, summary, errors, warnings):
    valid_count = 0
    summary["checked_object_count"] += 1
    if not isinstance(payload, list):
        add_error(summary, errors, f"{payload_name} must be array")
        return valid_count

    for i, item in enumerate(payload):
        summary["checked_object_count"] += 1
        row_label = f"{payload_name}[{i}]"
        if not isinstance(item, dict):
            add_error(summary, errors, f"{row_label} is not object")
            continue

        if check_required_keys(item, PRICE_RANGE_REQUIRED_NONEMPTY, row_label, summary, errors):
            valid_count += 1
        if check_has_keys_any(item, ["id", "price_range_id"], row_label, summary, errors):
            valid_count += 1
        check_upload_stage(item, row_label, summary, errors)
        if item.get("schema_version") in (None, ""):
            summary["missing_required_field_count"] += 1
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} has empty schema_version")
    scan_forbidden_fields(payload, payload_name, summary, warnings)
    return valid_count


def validate_price_range_review_payload(payload, payload_name, summary, errors, warnings):
    valid_count = 0
    summary["checked_object_count"] += 1
    if not isinstance(payload, list):
        add_error(summary, errors, f"{payload_name} must be array")
        return valid_count

    for i, item in enumerate(payload):
        summary["checked_object_count"] += 1
        row_label = f"{payload_name}[{i}]"
        if not isinstance(item, dict):
            add_error(summary, errors, f"{row_label} is not object")
            continue

        ok = True
        if not check_required_nonempty(item, ["canonical_item_code", "unit_normalized", "work_material_scope", "region_normalized", "currency", "group_key_summary", "created_at", "updated_at", "schema_version", "upload_stage"], row_label, summary, errors):
            ok = False
        if not check_has_keys_any(item, ["id", "price_range_id"], row_label, summary, errors):
            ok = False
        if ok:
            valid_count += 1
        check_upload_stage(item, row_label, summary, errors)
    scan_forbidden_fields(payload, payload_name, summary, warnings)
    return valid_count


def validate_price_range_decision_payload(payload, payload_name, summary, errors, warnings):
    valid_count = 0
    summary["checked_object_count"] += 1
    if not isinstance(payload, list):
        add_error(summary, errors, f"{payload_name} must be array")
        return valid_count

    for i, item in enumerate(payload):
        summary["checked_object_count"] += 1
        row_label = f"{payload_name}[{i}]"
        if not isinstance(item, dict):
            add_error(summary, errors, f"{row_label} is not object")
            continue

        ok = True
        if not check_required_nonempty(item, PRICE_RANGE_DECISION_REQUIRED_NONEMPTY, row_label, summary, errors):
            ok = False
        if item.get("decision") not in PRICE_RANGE_DECISIONS:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} decision invalid: {item.get('decision')}")
            ok = False
        if item.get("suggested_decision") not in PRICE_RANGE_DECISIONS:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} suggested_decision invalid: {item.get('suggested_decision')}")
            ok = False
        check_upload_stage(item, row_label, summary, errors)
        if ok:
            valid_count += 1
    scan_forbidden_fields(payload, payload_name, summary, warnings)
    return valid_count


def validate_price_range_override_payload(payload, payload_name, summary, errors, warnings):
    valid_count = 0
    summary["checked_object_count"] += 1
    if not isinstance(payload, list):
        add_error(summary, errors, f"{payload_name} must be array")
        return valid_count

    for i, item in enumerate(payload):
        summary["checked_object_count"] += 1
        row_label = f"{payload_name}[{i}]"
        if not isinstance(item, dict):
            add_error(summary, errors, f"{row_label} is not object")
            continue

        ok = True
        if not check_required_nonempty(item, PRICE_RANGE_OVERRIDE_REQUIRED_NONEMPTY, row_label, summary, errors):
            ok = False
        if not check_has_keys_any(item, ["id", "override_id", "price_range_id"], row_label, summary, errors):
            ok = False
        if item.get("previous_decision") not in PRICE_RANGE_DECISIONS:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} previous_decision invalid: {item.get('previous_decision')}")
            ok = False
        if item.get("requested_decision") not in PRICE_RANGE_DECISIONS:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} requested_decision invalid: {item.get('requested_decision')}")
            ok = False
        if "upload_stage" in item:
            check_upload_stage(item, row_label, summary, errors)
        if ok:
            valid_count += 1
    scan_forbidden_fields(payload, payload_name, summary, warnings)
    return valid_count


def validate_price_range_reviewed_with_audit_payload(payload, payload_name, summary, errors, warnings):
    valid_count = 0
    summary["checked_object_count"] += 1
    if not isinstance(payload, list):
        add_error(summary, errors, f"{payload_name} must be array")
        return valid_count

    for i, item in enumerate(payload):
        summary["checked_object_count"] += 1
        row_label = f"{payload_name}[{i}]"
        if not isinstance(item, dict):
            add_error(summary, errors, f"{row_label} is not object")
            continue

        ok = True
        if not check_required_keys(item, PRICE_RANGE_REQUIRED_NONEMPTY, row_label, summary, errors):
            ok = False
        if not check_required_nonempty(item, PRICE_RANGE_REVIEWED_WITH_AUDIT_REQUIRED_NONEMPTY, row_label, summary, errors):
            ok = False
        if not check_has_keys_any(item, ["id", "price_range_id"], row_label, summary, errors):
            ok = False
        if item.get("review_decision") not in PRICE_RANGE_DECISIONS:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} review_decision invalid: {item.get('review_decision')}")
            ok = False
        if item.get("suggested_decision") not in PRICE_RANGE_DECISIONS:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} suggested_decision invalid: {item.get('suggested_decision')}")
            ok = False
        if item.get("previous_decision") not in PRICE_RANGE_DECISIONS:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} previous_decision invalid: {item.get('previous_decision')}")
            ok = False
        if item.get("final_decision") not in PRICE_RANGE_DECISIONS:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} final_decision invalid: {item.get('final_decision')}")
            ok = False
        check_upload_stage(item, row_label, summary, errors)
        if ok:
            valid_count += 1
    scan_forbidden_fields(payload, payload_name, summary, warnings)
    return valid_count


def validate_price_range_audit_log_payload(payload, payload_name, summary, errors, warnings):
    valid_count = 0
    summary["checked_object_count"] += 1
    if not isinstance(payload, list):
        add_error(summary, errors, f"{payload_name} must be array")
        return valid_count

    for i, item in enumerate(payload):
        summary["checked_object_count"] += 1
        row_label = f"{payload_name}[{i}]"
        if not isinstance(item, dict):
            add_error(summary, errors, f"{row_label} is not object")
            continue

        ok = True
        if not check_required_nonempty(item, PRICE_RANGE_AUDIT_LOG_REQUIRED_NONEMPTY, row_label, summary, errors):
            ok = False
        if not check_has_keys_any(item, ["id", "audit_event_id", "price_range_id"], row_label, summary, errors):
            ok = False
        if item.get("event_type") not in PRICE_RANGE_AUDIT_EVENT_TYPES:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} event_type invalid: {item.get('event_type')}")
            ok = False
        if item.get("previous_decision") not in PRICE_RANGE_DECISIONS:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} previous_decision invalid: {item.get('previous_decision')}")
            ok = False
        if item.get("requested_decision") not in PRICE_RANGE_DECISIONS:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} requested_decision invalid: {item.get('requested_decision')}")
            ok = False
        if item.get("final_decision") not in PRICE_RANGE_DECISIONS:
            summary["error_count"] += 1
            add_error(summary, errors, f"{row_label} final_decision invalid: {item.get('final_decision')}")
            ok = False
        if "upload_stage" in item:
            check_upload_stage(item, row_label, summary, errors)
        if ok:
            valid_count += 1
    scan_forbidden_fields(payload, payload_name, summary, warnings)
    return valid_count


def check_one_of_observation_id(obj, label, summary, errors):
    if "observation_id" not in obj and "id" not in obj:
        summary["missing_required_field_count"] += 1
        summary["error_count"] += 1
        add_error(summary, errors, f"{label} missing required field (observation_id or id)")


def main():
    summary = {
        "checked_file_count": 0,
        "checked_object_count": 0,
        "valid_object_count": 0,
        "error_count": 0,
        "warning_count": 0,
        "forbidden_field_hit_count": 0,
        "missing_required_field_count": 0,
        "upload_stage_invalid_count": 0,
        "formal_price_generated": False,
        "formal_pricing_rule_generated": False,
        "budget_estimate_line_generated": False,
        "supabase_connected": False,
        "migration_generated": False,
    }

    errors = []
    warnings = []

    for name, path in PAYLOAD_PATHS.items():
        ok, payload, err = read_json(path)
        if not ok:
            add_error(summary, errors, f"{name} invalid json: {err}")
            continue
        summary["checked_file_count"] += 1

        if name == "sample_raw_catalog_source.json":
            summary["valid_object_count"] += validate_source_payload(payload, summary, errors, warnings)
        elif name in (
            "sample_price_observations.json",
            "sample_alias_edge_case_price_observations.json",
            "sample_alias_negative_context_price_observations.json",
        ):
            summary["valid_object_count"] += validate_observation_payload(payload, name, summary, errors, warnings)
        elif name in (
            "sample_price_observation_review_queue.json",
            "sample_alias_edge_case_review_queue.json",
            "sample_alias_negative_context_review_queue.json",
        ):
            summary["valid_object_count"] += validate_review_payload(
                payload,
                name,
                summary,
                errors,
                warnings,
                extra_required=[
                    "source_file_id",
                    "source_row_id",
                    "created_at",
                    "updated_at",
                    "schema_version",
                    "upload_stage",
                    "requires_human_review",
                ],
                key_only_extra=[
                    "observation_id",
                    "id",
                    "canonical_item_code",
                    "observed_unit_price",
                    "normalized_unit_price",
                    "unit_raw",
                    "unit_normalized",
                ],
            )
        elif name == "sample_price_ranges.json":
            summary["valid_object_count"] += validate_price_range_payload(payload, name, summary, errors, warnings)
        elif name == "sample_price_range_review_queue.json":
            summary["valid_object_count"] += validate_price_range_review_payload(payload, name, summary, errors, warnings)
        elif name == "sample_price_range_review_decisions.json":
            summary["valid_object_count"] += validate_price_range_decision_payload(payload, name, summary, errors, warnings)
        elif name == "sample_price_ranges_reviewed.json":
            summary["valid_object_count"] += validate_price_range_payload(payload, name, summary, errors, warnings)
        elif name == "sample_price_range_review_overrides.json":
            summary["valid_object_count"] += validate_price_range_override_payload(payload, name, summary, errors, warnings)
        elif name == "sample_price_ranges_reviewed_with_audit.json":
            summary["valid_object_count"] += validate_price_range_reviewed_with_audit_payload(payload, name, summary, errors, warnings)
        elif name == "sample_price_range_review_audit_log.json":
            summary["valid_object_count"] += validate_price_range_audit_log_payload(payload, name, summary, errors, warnings)
        elif name == "sample_quote_row_review_queue.json":
            summary["valid_object_count"] += validate_review_payload(payload, name, summary, errors, warnings)
        else:
            summary["valid_object_count"] += validate_review_payload(
                payload,
                name,
                summary,
                errors,
                warnings,
            )

    summary["warning_count"] = len(warnings)

    print("cloud payload validation summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        print(json.dumps({"errors": errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
