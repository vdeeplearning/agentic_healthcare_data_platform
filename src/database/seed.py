"""Backward-compatible CLI for deterministic synthetic SQLite datasets."""
from __future__ import annotations

import argparse
from pathlib import Path

from src.database.sqlite_loader import SQLiteSyntheticDatasetLoader, legacy_counts


def generate_dataset(path: Path, seed: int = 42, patients: int = 25_000, encounters: int = 100_000):
    """Generate logical records and load them into SQLite, returning a manifest-rich result."""
    return SQLiteSyntheticDatasetLoader().generate(path, seed, patients, encounters)


def generate_database(path: Path, seed: int = 42, patients: int = 25_000, encounters: int = 100_000) -> dict[str, int]:
    """Compatibility API retaining arguments, side effects, and return shape."""
    return legacy_counts(generate_dataset(path, seed, patients, encounters).row_counts)


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--path",type=Path,default=Path("data/generated/clinical.db")); parser.add_argument("--seed",type=int,default=42); parser.add_argument("--patients",type=int,default=25_000); parser.add_argument("--encounters",type=int,default=100_000)
    args=parser.parse_args(); print(generate_database(args.path,args.seed,args.patients,args.encounters))


if __name__ == "__main__": main()
