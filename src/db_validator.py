import sqlite3
from pathlib import Path

from src.schema import COLUMNS

DB_PATH = Path("data/generated/tickets.db")


def validate_database(db_path=DB_PATH):
    db_path = Path(db_path)
    errors = []
    counts = {}

    if not db_path.exists():
        return [f"Database not found: {db_path}"], counts

    connection = sqlite3.connect(db_path)

    try:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchall()

        if integrity != [("ok",)]:
            errors.append(f"Integrity check failed: {integrity}")

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if foreign_key_errors:
            errors.append(
                f"Foreign-key violations: {foreign_key_errors[:10]}"
            )

        existing_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

        expected_tables = set(COLUMNS.keys())
        missing_tables = expected_tables - existing_tables

        if missing_tables:
            errors.append(f"Missing tables: {sorted(missing_tables)}")

        for table in COLUMNS:
            if table in existing_tables:
                count = connection.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]

                counts[table] = count

                if count == 0:
                    errors.append(f"Table is empty: {table}")

        return errors, counts

    finally:
        connection.close()


if __name__ == "__main__":
    errors, counts = validate_database()

    print("Database record counts:")
    for table, count in counts.items():
        print(f"{table}: {count}")

    if errors:
        print("\nDATABASE VALIDATION FAILED")
        for error in errors:
            print(error)
        raise SystemExit(1)

    print("\nDATABASE VALIDATION PASSED")