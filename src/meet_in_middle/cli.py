from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict

from .data import Scenario, TravelDataset
from .solver import solve_scenario


def load_scenario(path: Path) -> Scenario:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return Scenario.from_payload(payload)


def load_dataset(path: Path) -> TravelDataset:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        records = list(reader)
    return TravelDataset.from_records(records)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Meet-In-Middle solver CLI")
    parser.add_argument("scenario", type=Path, help="Path to scenario JSON file")
    parser.add_argument("connections", type=Path, help="Path to connections CSV file")
    parser.add_argument("--duration-weight", type=float, default=0.6, help="Weight for travel time when ranking routes")
    parser.add_argument("--emission-weight", type=float, default=0.4, help="Weight for emissions when ranking routes")
    parser.add_argument(
        "--host-weight",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override host scoring weight (e.g. total_co2=0.5). Can be passed multiple times.",
    )
    parser.add_argument(
        "--alternatives",
        type=int,
        default=0,
        help="Number of alternative host locations to include in the output",
    )
    args = parser.parse_args(argv)

    scenario = load_scenario(args.scenario)
    dataset = load_dataset(args.connections)

    weights: Dict[str, float] | None = None
    if args.host_weight:
        weights = {}
        for override in args.host_weight:
            if "=" not in override:
                raise ValueError(f"Invalid host weight override: {override}")
            key, value = override.split("=", 1)
            weights[key] = float(value)

    result = solve_scenario(
        scenario,
        dataset,
        route_preference=(args.duration_weight, args.emission_weight),
        weights=weights,
        include_alternatives=args.alternatives,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
