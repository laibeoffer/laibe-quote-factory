import argparse
import json
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

from generate_price_observations_from_rows import run_generation


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT_DIR / "samples" / "sample_alias_edge_case_rows.json"
DEFAULT_OUTPUT = ROOT_DIR / "exports_to_raw_warehouse" / "sample_alias_edge_case_price_observations.json"
DEFAULT_REVIEW_OUTPUT = ROOT_DIR / "review_queue" / "sample_alias_edge_case_review_queue.json"


def parse_args():
    parser = argparse.ArgumentParser(description="Test alias confidence scoring for sample edge cases.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--review-output", default=str(DEFAULT_REVIEW_OUTPUT))
    return parser.parse_args()


def main():
    args = parse_args()
    _, observations, _ = run_generation(
        Path(args.input),
        Path(args.output),
        Path(args.review_output),
    )

    test_case_count = len(observations)
    auto_matched_count = 0
    low_confidence_review_count = 0
    unmatched_review_count = 0
    negative_context_review_count = 0
    unsafe_auto_match_count = 0

    for obs in observations:
        alias_meta = obs.get("alias_meta", {})
        warnings = obs.get("warnings", [])
        if alias_meta.get("auto_matched"):
            auto_matched_count += 1

        if "alias_low_confidence" in warnings:
            low_confidence_review_count += 1

        if obs.get("canonical_item_code") is None and obs.get("requires_human_review"):
            unmatched_review_count += 1

        if "alias_negative_context_hit" in warnings:
            negative_context_review_count += 1
            if not obs.get("requires_human_review", False):
                unsafe_auto_match_count += 1

        if "alias_negative_context_hit" not in warnings and alias_meta.get("negative_hits"):
            unsafe_auto_match_count += 1 if not obs.get("requires_human_review", False) else 0

    summary = {
        "test_case_count": test_case_count,
        "auto_matched_count": auto_matched_count,
        "low_confidence_review_count": low_confidence_review_count,
        "unmatched_review_count": unmatched_review_count,
        "negative_context_review_count": negative_context_review_count,
        "unsafe_auto_match_count": unsafe_auto_match_count,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
