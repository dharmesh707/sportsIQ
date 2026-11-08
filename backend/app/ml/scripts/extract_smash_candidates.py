from pathlib import Path
import argparse
import zipfile

import pandas as pd


# Columns that are useful for reviewing candidate smash records.
PREFERRED_COLUMNS = [
    "match_id",
    "set",
    "rally",
    "ball_round",
    "player",
    "player_location",
    "opponent_location",
    "shot_type",
    "shot_type_en",
    "landing",
    "aroundhead",
    "backhand",
    "player_x",
    "player_y",
    "opponent_x",
    "opponent_y",
    "video_url",
    "youtube_url",
]


def read_csv_from_zip(zip_path: Path, csv_name: str) -> pd.DataFrame:
    """Read a CSV file from a ZIP archive by filename."""
    with zipfile.ZipFile(zip_path, "r") as archive:
        matches = [
            name
            for name in archive.namelist()
            if Path(name).name.lower() == csv_name.lower()
        ]

        if not matches:
            available_csvs = [
                name for name in archive.namelist()
                if name.lower().endswith(".csv")
            ]
            raise FileNotFoundError(
                f"Could not find {csv_name} inside {zip_path}.\n"
                f"CSV files found:\n{available_csvs}"
            )

        with archive.open(matches[0]) as file:
            return pd.read_csv(file)


def main():
    parser = argparse.ArgumentParser(
        description="Extract badminton smash candidate records from ShuttleSet."
    )

    parser.add_argument(
        "--zip",
        required=True,
        help="Path to the ShuttleSet dataset ZIP file.",
    )

    parser.add_argument(
        "--csv",
        default="badminton_shuttleset_master.csv",
        help="CSV filename inside the ZIP archive.",
    )

    parser.add_argument(
        "--output",
        default="backend/ml/datasets/smash_review",
        help="Directory where output CSV files will be saved.",
    )

    args = parser.parse_args()

    zip_path = Path(args.zip)
    output_dir = Path(args.output)

    if not zip_path.exists():
        raise FileNotFoundError(f"Dataset ZIP not found: {zip_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading dataset: {zip_path}")

    df = read_csv_from_zip(zip_path, args.csv)

    if "shot_type_en" not in df.columns:
        raise KeyError(
            "Expected column 'shot_type_en' was not found.\n"
            f"Available columns: {list(df.columns)}"
        )

    # Normalize text for matching without modifying the original column.
    shot_types = df["shot_type_en"].astype("string").str.strip().str.lower()

    # Keep the original labels separate for review.
    smash_df = df.loc[shot_types == "smash"].copy()
    wrist_smash_df = df.loc[shot_types == "wrist smash"].copy()

    # Combine candidate categories, but do not claim all are confirmed
    # overhead smashes. They need review.
    smash_df["candidate_group"] = "smash"
    wrist_smash_df["candidate_group"] = "wrist_smash_review"

    candidates = pd.concat(
        [smash_df, wrist_smash_df],
        ignore_index=True,
    )

    # Preserve useful columns that actually exist in this dataset.
    available_columns = [
        column for column in PREFERRED_COLUMNS
        if column in candidates.columns
    ]

    output_columns = available_columns + [
        column for column in ["candidate_group"]
        if column not in available_columns
    ]

    candidates = candidates[output_columns]

    # Save outputs.
    smash_output = output_dir / "smash_candidates.csv"
    wrist_output = output_dir / "wrist_smash_review.csv"
    combined_output = output_dir / "all_smash_candidates.csv"
    summary_output = output_dir / "audit_summary.csv"

    smash_df.to_csv(smash_output, index=False)
    wrist_smash_df.to_csv(wrist_output, index=False)
    candidates.to_csv(combined_output, index=False)

    summary = pd.DataFrame(
        {
            "category": [
                "total_dataset_rows",
                "smash_records",
                "wrist_smash_records",
                "combined_candidates",
            ],
            "count": [
                len(df),
                len(smash_df),
                len(wrist_smash_df),
                len(candidates),
            ],
        }
    )

    summary.to_csv(summary_output, index=False)

    print("\nExtraction complete.")
    print(summary.to_string(index=False))

    print("\nOutput files:")
    print(smash_output)
    print(wrist_output)
    print(combined_output)
    print(summary_output)


if __name__ == "__main__":
    main()