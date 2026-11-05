
from __future__ import annotations

import re
import sys
from collections import Counter

from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import Engine

from app.config import get_settings


# Exact snapshot we inspected before approving this migration.
EXPECTED_LOCAL = {
    "users": 137,
    "analyses": 100,
    "faults": 182,
    "health_data": 5,
}

EXPECTED_REMOTE = {
    "users": 30,
    "analyses": 16,
    "faults": 30,
    "health_data": 1,
}

TABLES = ["users", "analyses", "faults", "health_data"]

# Test-generated user emails observed in Supabase.
TEST_EMAIL_PATTERN = re.compile(r"^test_[0-9a-f]{8}@example\.com$", re.IGNORECASE)


def load_tables(engine: Engine) -> dict:
    metadata = MetaData()
    metadata.reflect(bind=engine, only=TABLES)
    return {name: metadata.tables[name] for name in TABLES}


def count_rows(engine: Engine, tables: dict) -> dict[str, int]:
    with engine.connect() as conn:
        return {
            name: conn.execute(
                select(text("COUNT(*)")).select_from(tables[name])
            ).scalar_one()
            for name in TABLES
        }


def read_all(engine: Engine, table) -> list[dict]:
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(select(table)).mappings().all()]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    source_engine = create_engine("sqlite:///./sportsiq.db")
    target_engine = create_engine(get_settings().database_url)

    try:
        source_tables = load_tables(source_engine)
        target_tables = load_tables(target_engine)

        source_counts = count_rows(source_engine, source_tables)
        target_counts = count_rows(target_engine, target_tables)

        print("\n=== Pre-migration counts ===")
        print("Local SQLite:", source_counts)
        print("Supabase:", target_counts)

        require(
            source_counts == EXPECTED_LOCAL,
            "Local counts differ from the inspected snapshot. Stopping.",
        )
        require(
            target_counts == EXPECTED_REMOTE,
            "Supabase counts differ from the inspected snapshot. Stopping.",
        )

        # Read and validate the current hosted test data.
        remote_users = read_all(target_engine, target_tables["users"])
        remote_analyses = read_all(target_engine, target_tables["analyses"])
        remote_faults = read_all(target_engine, target_tables["faults"])
        remote_health = read_all(target_engine, target_tables["health_data"])

        test_user_ids = {str(row["id"]) for row in remote_users}
        test_analysis_ids = {str(row["id"]) for row in remote_analyses}

        require(
            all(TEST_EMAIL_PATTERN.fullmatch(row["email"]) for row in remote_users),
            "At least one hosted user is not a matching test account. Stopping.",
        )
        require(
            all(str(row["user_id"]) in test_user_ids for row in remote_analyses),
            "A hosted analysis belongs to a user outside the test-user set. Stopping.",
        )
        require(
            all(str(row["analysis_id"]) in test_analysis_ids for row in remote_faults),
            "A hosted fault belongs to an analysis outside the test set. Stopping.",
        )
        require(
            all(str(row["user_id"]) in test_user_ids for row in remote_health),
            "A hosted health record belongs to a user outside the test set. Stopping.",
        )

        # Read local records.
        local_rows = {
            name: read_all(source_engine, source_tables[name])
            for name in TABLES
        }

        # Check all local primary keys against the hosted primary keys.
        for name in TABLES:
            source_pk = inspect(source_engine).get_pk_constraint(name)["constrained_columns"]
            target_pk = inspect(target_engine).get_pk_constraint(name)["constrained_columns"]

            require(
                source_pk == target_pk and len(source_pk) == 1,
                f"Primary-key structure differs for {name}. Stopping.",
            )

            key = source_pk[0]
            local_ids = {str(row[key]) for row in local_rows[name]}
            remote_ids = {str(row[key]) for row in read_all(target_engine, target_tables[name])}

            require(
                not (local_ids & remote_ids),
                f"Primary-key overlap found in {name}. Stopping.",
            )

        print("\nAll preflight checks passed.")
        print("The script is ready to replace the hosted test rows with local data.")
        print("\nHosted rows to remove:", EXPECTED_REMOTE)
        print("Local rows to import:", EXPECTED_LOCAL)

        confirmation = input(
            '\nType exactly "MIGRATE SPORTS IQ DATA" to proceed: '
        ).strip()

        if confirmation != "MIGRATE SPORTS IQ DATA":
            print("Confirmation did not match. No database changes made.")
            return

        # One PostgreSQL transaction: cleanup + import + verification.
        with target_engine.begin() as conn:
            # Delete children before parents.
            conn.execute(target_tables["faults"].delete())
            conn.execute(target_tables["analyses"].delete())
            conn.execute(target_tables["health_data"].delete())
            conn.execute(target_tables["users"].delete())

            # Insert parents before children.
            for name in ["users", "analyses", "faults", "health_data"]:
                rows = local_rows[name]
                if rows:
                    conn.execute(target_tables[name].insert(), rows)

            # Verify counts inside the transaction before commit.
            final_counts = {
                name: conn.execute(
                    select(text("COUNT(*)")).select_from(target_tables[name])
                ).scalar_one()
                for name in TABLES
            }

            require(
                final_counts == EXPECTED_LOCAL,
                f"Final counts do not match expected values: {final_counts}",
            )

            # Verify foreign-key integrity on the destination.
            violations = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM analyses a
                    LEFT JOIN users u ON u.id = a.user_id
                    WHERE u.id IS NULL
                """)
            ).scalar_one()
            require(violations == 0, "Orphaned analyses found.")

            violations = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM faults f
                    LEFT JOIN analyses a ON a.id = f.analysis_id
                    WHERE a.id IS NULL
                """)
            ).scalar_one()
            require(violations == 0, "Orphaned faults found.")

            violations = conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM health_data h
                    LEFT JOIN users u ON u.id = h.user_id
                    WHERE u.id IS NULL
                """)
            ).scalar_one()
            require(violations == 0, "Orphaned health records found.")

        print("\nMigration committed successfully.")
        print("Final Supabase counts:", final_counts)
        print("Foreign-key checks: passed")

    except Exception as exc:
        print("\nMIGRATION STOPPED:", exc)
        print("If the transaction had started, its changes were rolled back.")
        sys.exit(1)

    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    main()
