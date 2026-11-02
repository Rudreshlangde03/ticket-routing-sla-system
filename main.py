
import argparse
from pathlib import Path

from src.data_generator import generate
from src.validator import validate
from src.database import create_database

p = argparse.ArgumentParser()
s = p.add_subparsers(dest="cmd", required=True)

# Generate dataset
g = s.add_parser("generate")
g.add_argument("--tickets", type=int, default=500)
g.add_argument("--messages", type=int, default=1500)
g.add_argument("--agents", type=int, default=100)
g.add_argument("--seed", type=int, default=20261022)
g.add_argument("--output", type=Path, default=Path("data/generated"))

# Validate dataset
v = s.add_parser("validate")
v.add_argument("--input", type=Path, default=Path("data/generated"))

# Create SQLite database
s.add_parser("database")

a = p.parse_args()

if a.cmd == "generate":
    print(generate(a.tickets, a.messages, a.agents, a.seed, a.output))

elif a.cmd == "validate":
    errors, counts = validate(a.input)
    print(counts)

    if errors:
        print("\n".join(errors))
        raise SystemExit(1)

    print("VALIDATION PASSED")

elif a.cmd == "database":
    path, counts = create_database()

    print(f"Database created: {path}")

    for table, count in counts.items():
        print(f"{table}: {count}")
