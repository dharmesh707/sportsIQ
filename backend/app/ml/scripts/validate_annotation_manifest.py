"""CLI for structural validation of an annotation manifest CSV."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from app.ml.dataset.manifest_validator import (
    ManifestValidationOptions,
    validate_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a SportsIQ annotation manifest CSV."
    )
    parser.add_argument("manifest", type=Path, help="Annotation manifest CSV.")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        help="Root used to resolve source-video and feature CSV paths.",
    )
    parser.add_argument(
        "--strict-single-sequence",
        action="store_true",
        help="Reject movements that reference multiple sequences.",
    )
    parser.add_argument(
        "--split-assignments",
        type=Path,
        help="CSV with video_id,split and optional player_id columns.",
    )
    parser.add_argument(
        "--check-player-split-leakage",
        action="store_true",
        help="Reject players assigned to multiple splits.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit deterministic JSON diagnostics.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    split_assignments = None
    if args.split_assignments is not None:
        try:
            with args.split_assignments.open(
                newline="",
                encoding="utf-8",
            ) as file:
                split_assignments = list(csv.DictReader(file))
        except OSError as error:
            raise SystemExit(f"Cannot read split assignments: {error}") from error
    result = validate_manifest(
        args.manifest,
        ManifestValidationOptions(
            dataset_root=args.dataset_root,
            require_single_sequence_per_movement=args.strict_single_sequence,
            split_assignments=split_assignments,
            check_player_split_leakage=args.check_player_split_leakage,
        ),
    )
    if args.json_output:
        print(json.dumps({
            "valid": result.valid,
            "row_count": result.row_count,
            "diagnostics": [
                {
                    "severity": item.severity,
                    "row_number": item.row_number,
                    "field": item.field,
                    "message": item.message,
                }
                for item in result.diagnostics
            ],
        }, sort_keys=True))
    else:
        for item in result.diagnostics:
            location = (
                f"row {item.row_number}" if item.row_number is not None
                else "manifest"
            )
            field = f" [{item.field}]" if item.field else ""
            print(f"{item.severity.upper()}: {location}{field}: {item.message}")
        print(f"Rows: {result.row_count}; valid: {result.valid}")
    raise SystemExit(0 if result.valid else 1)


if __name__ == "__main__":
    main()
