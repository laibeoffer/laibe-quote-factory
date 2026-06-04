import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT_DIR / "exports_to_raw_warehouse" / "cloud_ready_export_package.json"
MANIFEST_PATH = ROOT_DIR / "exports_to_raw_warehouse" / "export_manifest.json"

FORBIDDEN_EXACT_KEYS = {
    "formal_price",
    "approved_price",
    "official_unit_price",
    "PricingRule",
    "MaterialSpec",
    "LaborRule",
    "BudgetEstimateLine",
    "BudgetOutputSnapshot",
}

FORBIDDEN_PAYLOAD_KEYS = {
    "supabase_url",
    "supabase_payload",
    "api_endpoint",
    "api_payload",
    "migration_id",
    "migration_payload",
    "renderer_payload",
    "renderer_output",
}

FALSE_FLAGS = [
    "formal_price_generated",
    "formal_pricing_rule_generated",
    "budget_estimate_line_generated",
]

BOUNDARY_FALSE_FLAGS = [
    "supabase_connected",
    "api_connected",
    "migration_generated",
    "renderer_output_generated",
]

ALLOWED_HANDOFF_TARGETS = {"raw_candidate_warehouse", "review"}
ALLOWED_DOWNSTREAM = {"raw_candidate_warehouse", "pricing_method_review", "review_queue"}
REQUIRED_DOWNSTREAM_FORBIDDEN = {
    "Budget Engine",
    "Renderer",
    "BudgetOutputSnapshot",
    "customer_view",
    "PricingRule direct publish",
    "BudgetEstimateLine.unit_price",
}

REQUIREMENT_CONTEXT_KEYS = {
    "project_id",
    "owner_intent_id",
    "project_requirement_brief_id",
    "requirement_context_status",
    "requirement_context_source",
    "metadata_only",
    "affects_observation_values",
    "affects_range_values",
}
REQUIREMENT_CONTEXT_STATUSES = {"placeholder", "linked", "verified", "unavailable"}
REQUIREMENT_CONTEXT_SOURCES = {"owner_guide_placeholder", "owner_guide_contract", "none"}

PLAN_CONTEXT_KEYS = {
    "plan_id",
    "svg_artifact_id",
    "plan_source_type",
    "plan_quantity_facts_id",
    "plan_context_status",
    "metadata_only",
    "affects_observation_values",
    "affects_range_values",
}
PLAN_SOURCE_TYPES = {"svg", "png", "jpg", "pdf", "placeholder", "none"}
PLAN_CONTEXT_STATUSES = {"placeholder", "linked", "verified", "unavailable"}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def count_objects(payload):
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        return 1
    return 0


def schema_versions(payload):
    if isinstance(payload, list):
        return sorted(
            {
                item.get("schema_version")
                for item in payload
                if isinstance(item, dict) and item.get("schema_version")
            }
        )
    if isinstance(payload, dict) and payload.get("schema_version"):
        return [payload["schema_version"]]
    return []


def collect_key_hits(payload, path, forbidden_keys, hits):
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in forbidden_keys:
                hits.append({"path": path, "key": key})
            collect_key_hits(value, f"{path}.{key}", forbidden_keys, hits)
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            collect_key_hits(item, f"{path}[{index}]", forbidden_keys, hits)


def require_false(errors, source_name, payload, key):
    if payload.get(key) is not False:
        errors.append(f"{source_name}.{key}_must_be_false")


def validate_context_window(errors, name, window, allowed_keys, status_key, allowed_statuses):
    if not isinstance(window, dict):
        errors.append(f"{name}_must_be_object")
        return False

    extra_keys = sorted(set(window) - allowed_keys)
    if extra_keys:
        errors.append(f"{name}_has_unexpected_keys:{','.join(extra_keys)}")

    for key in window:
        lowered = key.lower()
        if "price" in lowered or "pricing" in lowered or "budgetestimateline" in lowered:
            errors.append(f"{name}_must_not_define_price_key:{key}")

    if window.get(status_key) not in allowed_statuses:
        errors.append(f"{name}_{status_key}_invalid:{window.get(status_key)}")

    if window.get("metadata_only") is not True:
        errors.append(f"{name}_metadata_only_must_be_true")
    if window.get("affects_observation_values") is not False:
        errors.append(f"{name}_affects_observation_values_must_be_false")
    if window.get("affects_range_values") is not False:
        errors.append(f"{name}_affects_range_values_must_be_false")

    return True


def validate():
    errors = []
    forbidden_key_hits = []
    forbidden_payload_key_hits = []
    actual_counts = {}
    actual_schema_versions = {}

    if not PACKAGE_PATH.exists():
        errors.append("package_file_missing")
        package = {}
    else:
        package = load_json(PACKAGE_PATH)

    if not MANIFEST_PATH.exists():
        errors.append("manifest_file_missing")
        manifest = {}
    else:
        manifest = load_json(MANIFEST_PATH)

    package_files = package.get("included_files", [])
    manifest_files = manifest.get("files", [])
    manifest_file_paths = [item.get("path") for item in manifest_files if isinstance(item, dict)]

    if not isinstance(package_files, list) or not package_files:
        errors.append("package_included_files_missing")
        package_files = []

    if sorted(package_files) != sorted(manifest_file_paths):
        errors.append("package_included_files_must_match_manifest_files")

    required_package_refs = [
        "price_observation_file",
        "price_range_file",
        "reviewed_price_range_file",
        "audit_log_file",
        "review_decision_file",
    ]
    for ref_key in required_package_refs:
        ref_path = package.get(ref_key)
        if ref_path not in package_files:
            errors.append(f"{ref_key}_must_be_in_included_files")

    checked_object_count = 0
    for rel_path in package_files:
        path = ROOT_DIR / rel_path
        if not path.exists():
            errors.append(f"included_file_missing:{rel_path}")
            continue
        payload = load_json(path)
        actual_count = count_objects(payload)
        actual_counts[rel_path] = actual_count
        actual_schema_versions[rel_path] = schema_versions(payload)
        checked_object_count += actual_count
        collect_key_hits(payload, rel_path, FORBIDDEN_EXACT_KEYS, forbidden_key_hits)
        collect_key_hits(payload, rel_path, FORBIDDEN_PAYLOAD_KEYS, forbidden_payload_key_hits)

    collect_key_hits(package, "cloud_ready_export_package.json", FORBIDDEN_EXACT_KEYS, forbidden_key_hits)
    collect_key_hits(manifest, "export_manifest.json", FORBIDDEN_EXACT_KEYS, forbidden_key_hits)
    collect_key_hits(package, "cloud_ready_export_package.json", FORBIDDEN_PAYLOAD_KEYS, forbidden_payload_key_hits)
    collect_key_hits(manifest, "export_manifest.json", FORBIDDEN_PAYLOAD_KEYS, forbidden_payload_key_hits)

    manifest_counts = manifest.get("object_counts", {})
    if not isinstance(manifest_counts, dict):
        errors.append("manifest_object_counts_must_be_object")
        manifest_counts = {}
    for rel_path, actual_count in actual_counts.items():
        if manifest_counts.get(rel_path) != actual_count:
            errors.append(f"object_count_mismatch:{rel_path}:expected={manifest_counts.get(rel_path)}:actual={actual_count}")

    manifest_schema_versions = manifest.get("schema_versions", {})
    if not isinstance(manifest_schema_versions, dict):
        errors.append("manifest_schema_versions_must_be_object")
        manifest_schema_versions = {}
    for rel_path, versions in actual_schema_versions.items():
        if manifest_schema_versions.get(rel_path) != versions:
            errors.append(
                f"schema_versions_mismatch:{rel_path}:expected={manifest_schema_versions.get(rel_path)}:actual={versions}"
            )

    for file_entry in manifest_files:
        if not isinstance(file_entry, dict):
            errors.append("manifest_file_entry_must_be_object")
            continue
        rel_path = file_entry.get("path")
        if rel_path in actual_counts and file_entry.get("object_count") != actual_counts[rel_path]:
            errors.append(f"manifest_file_object_count_mismatch:{rel_path}")
        if rel_path in actual_schema_versions and file_entry.get("schema_versions") != actual_schema_versions[rel_path]:
            errors.append(f"manifest_file_schema_versions_mismatch:{rel_path}")

    for key in FALSE_FLAGS:
        require_false(errors, "package", package, key)
        require_false(errors, "package.forbidden_field_summary", package.get("forbidden_field_summary", {}), key)

    for key in BOUNDARY_FALSE_FLAGS:
        require_false(errors, "package.forbidden_field_summary", package.get("forbidden_field_summary", {}), key)

    handoff_target = package.get("handoff_target")
    if handoff_target not in ALLOWED_HANDOFF_TARGETS:
        errors.append(f"handoff_target_invalid:{handoff_target}")

    downstream_allowed = set(manifest.get("downstream_allowed", []))
    if not downstream_allowed:
        errors.append("manifest_downstream_allowed_missing")
    if not downstream_allowed.issubset(ALLOWED_DOWNSTREAM):
        errors.append(f"manifest_downstream_allowed_invalid:{sorted(downstream_allowed - ALLOWED_DOWNSTREAM)}")

    downstream_forbidden = set(manifest.get("downstream_forbidden", []))
    missing_forbidden = sorted(REQUIRED_DOWNSTREAM_FORBIDDEN - downstream_forbidden)
    if missing_forbidden:
        errors.append(f"manifest_downstream_forbidden_missing:{','.join(missing_forbidden)}")

    requirement_window = package.get("requirement_context_window")
    if validate_context_window(
        errors,
        "requirement_context_window",
        requirement_window,
        REQUIREMENT_CONTEXT_KEYS,
        "requirement_context_status",
        REQUIREMENT_CONTEXT_STATUSES,
    ):
        if requirement_window.get("requirement_context_source") not in REQUIREMENT_CONTEXT_SOURCES:
            errors.append(
                f"requirement_context_window_source_invalid:{requirement_window.get('requirement_context_source')}"
            )

    plan_window = package.get("plan_context_window")
    if validate_context_window(
        errors,
        "plan_context_window",
        plan_window,
        PLAN_CONTEXT_KEYS,
        "plan_context_status",
        PLAN_CONTEXT_STATUSES,
    ):
        if plan_window.get("plan_source_type") not in PLAN_SOURCE_TYPES:
            errors.append(f"plan_context_window_source_type_invalid:{plan_window.get('plan_source_type')}")

    if forbidden_key_hits:
        errors.append("forbidden_exact_keys_found")
    if forbidden_payload_key_hits:
        errors.append("forbidden_payload_keys_found")

    summary = {
        "package_file_exists": PACKAGE_PATH.exists(),
        "manifest_file_exists": MANIFEST_PATH.exists(),
        "included_file_count": len(package_files),
        "checked_object_count": checked_object_count,
        "object_counts_match": not any(error.startswith("object_count_mismatch") for error in errors),
        "schema_versions_match": not any(error.startswith("schema_versions_mismatch") for error in errors),
        "forbidden_field_hit_count": len(forbidden_key_hits),
        "forbidden_payload_key_hit_count": len(forbidden_payload_key_hits),
        "formal_price_generated": package.get("formal_price_generated"),
        "formal_pricing_rule_generated": package.get("formal_pricing_rule_generated"),
        "budget_estimate_line_generated": package.get("budget_estimate_line_generated"),
        "supabase_connected": package.get("forbidden_field_summary", {}).get("supabase_connected"),
        "migration_generated": package.get("forbidden_field_summary", {}).get("migration_generated"),
        "renderer_output_generated": package.get("forbidden_field_summary", {}).get("renderer_output_generated"),
        "handoff_target": handoff_target,
        "requirement_context_window_metadata_only": isinstance(requirement_window, dict)
        and requirement_window.get("metadata_only") is True,
        "plan_context_window_metadata_only": isinstance(plan_window, dict) and plan_window.get("metadata_only") is True,
        "error_count": len(errors),
        "errors": errors,
    }

    print("cloud-ready export package validation summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if forbidden_key_hits:
        print(json.dumps({"forbidden_key_hits": forbidden_key_hits}, ensure_ascii=False, indent=2))
    if forbidden_payload_key_hits:
        print(json.dumps({"forbidden_payload_key_hits": forbidden_payload_key_hits}, ensure_ascii=False, indent=2))

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(validate())
