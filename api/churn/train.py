"""CLI entry point: python -m api.churn.train [--version 1.0.0]."""

from __future__ import annotations

import argparse
import json

from api.churn.training import train_and_save


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the Olist customer churn model from dbt marts")
    parser.add_argument("--version", help="Immutable semantic model version, e.g. 1.0.0")
    args = parser.parse_args()
    result = train_and_save(version=args.version)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
