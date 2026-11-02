
import csv
import sqlite3
from pathlib import Path

from src.schema import COLUMNS

DATA_DIR = Path("data/generated")
DB_PATH = DATA_DIR / "tickets.db"

IMPORT_ORDER = [
    "intents", "languages", "customers", "channels",
    "agents", "skills", "queues", "tickets", "messages",
    "priority_rules", "assignment_events", "sla_events",
    "resolutions", "agent_skills", "agent_languages",
    "ticket_events", "ground_truth",
]

PRIMARY_KEYS = {
    "customers": ["customer_id"],
    "channels": ["channel_id"],
    "tickets": ["ticket_id"],
    "messages": ["message_id"],
    "intents": ["intent_id"],
    "languages": ["language_id"],
    "priority_rules": ["priority_rule_id"],
    "agents": ["agent_id"],
    "skills": ["skill_id"],
    "queues": ["queue_id"],
    "assignment_events": ["assignment_id"],
    "sla_events": ["sla_id"],
    "resolutions": ["resolution_id"],
    "agent_skills": ["agent_id", "skill_id", "effective_from"],
    "agent_languages": ["agent_id", "language_id", "effective_from"],
    "ticket_events": ["event_id"],
    "ground_truth": ["anomaly_id"],
}

FOREIGN_KEYS = {
    "tickets": {
        "customer_id": ("customers", "customer_id"),
        "channel_id": ("channels", "channel_id"),
        "intent_id": ("intents", "intent_id"),
        "language_id": ("languages", "language_id"),
    },
    "messages": {
        "ticket_id": ("tickets", "ticket_id"),
        "channel_id": ("channels", "channel_id"),
        "language_id": ("languages", "language_id"),
    },
    "priority_rules": {
        "intent_id": ("intents", "intent_id"),
    },
    "assignment_events": {
        "ticket_id": ("tickets", "ticket_id"),
        "agent_id": ("agents", "agent_id"),
        "queue_id": ("queues", "queue_id"),
    },
    "sla_events": {"ticket_id": ("tickets", "ticket_id")},
    "resolutions": {"ticket_id": ("tickets", "ticket_id")},
    "agent_skills": {
        "agent_id": ("agents", "agent_id"),
        "skill_id": ("skills", "skill_id"),
    },
    "agent_languages": {
        "agent_id": ("agents", "agent_id"),
        "language_id": ("languages", "language_id"),
    },
    "ticket_events": {"ticket_id": ("tickets", "ticket_id")},
    "ground_truth": {"ticket_id": ("tickets", "ticket_id")},
}


def create_database(data_dir=DATA_DIR, db_path=DB_PATH):
    data_dir = Path(data_dir)
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        # Step 1: Remove old generated tables.
        for table in reversed(IMPORT_ORDER):
            connection.execute(
                f'DROP TABLE IF EXISTS "{table}"'
            )

        # Step 2: Create all tables.
        for table, columns in COLUMNS.items():
            definitions = [
                f'"{column}" TEXT' for column in columns
            ]

            keys = PRIMARY_KEYS.get(table, [])
            if keys:
                key_columns = ", ".join(
                    f'"{key}"' for key in keys
                )
                definitions.append(
                    f"PRIMARY KEY ({key_columns})"
                )

            for column, (parent, parent_column) in (
                FOREIGN_KEYS.get(table, {}).items()
            ):
                definitions.append(
                    f'FOREIGN KEY ("{column}") '
                    f'REFERENCES "{parent}"("{parent_column}")'
                )

            sql = (
                f'CREATE TABLE IF NOT EXISTS "{table}" '
                f'({", ".join(definitions)})'
            )
            connection.execute(sql)

        # Step 3: Import CSV data.
        for table in IMPORT_ORDER:
            print(f"Importing table: {table}")
            columns = COLUMNS[table]
            csv_path = data_dir / f"{table}.csv"

            if not csv_path.exists():
                raise FileNotFoundError(
                    f"Missing CSV: {csv_path}"
                )

            with csv_path.open(
                "r", newline="", encoding="utf-8-sig"
            ) as file:
                reader = csv.DictReader(file)

                if reader.fieldnames != columns:
                    raise ValueError(
                        f"CSV columns mismatch: {table}"
                    )

                placeholders = ", ".join(
                    "?" for _ in columns
                )
                column_names = ", ".join(
                    f'"{column}"' for column in columns
                )

                sql = (
                    f'INSERT INTO "{table}" ({column_names}) '
                    f'VALUES ({placeholders})'
                )

                rows = [
                    tuple(row[column] for column in columns)
                    for row in reader
                ]

                connection.executemany(sql, rows)

        # Step 4: Commit and verify.
        connection.commit()

        errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if errors:
            raise ValueError(
                f"Foreign-key violations: {errors[:10]}"
            )

        counts = {
            table: connection.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
            for table in COLUMNS
        }

        return db_path, counts

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    path, counts = create_database()
    print(f"Database created: {path}")

    for table, count in counts.items():
        print(f"{table}: {count}")
