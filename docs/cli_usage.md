# Meet-In-Middle Solver CLI

Run the optimisation engine directly from the command line.

## Prerequisites

- Python 3.11+
- Repository root as current working directory
- The `src` folder added to `PYTHONPATH`

For PowerShell users:

```powershell
$env:PYTHONPATH = (Resolve-Path src)
```

## Basic invocation

```powershell
python -m meet_in_middle.cli data/sample_scenario.json data/sample_connections.csv
```

Pass `--alternatives N` to include the top `N` non-selected host locations in the JSON output.

## Adjusting optimisation weights

- `--duration-weight` and `--emission-weight` control how the solver picks itineraries when multiple routes are Pareto optimal.
- `--host-weight key=value` overrides the composite score weights used when comparing host cities. Repeat the flag for multiple keys (e.g. `total_co2`, `gini_travel_hours`).

Example:

```powershell
python -m meet_in_middle.cli data/sample_scenario.json data/sample_connections.csv --duration-weight 0.4 --emission-weight 0.6 --host-weight total_co2=0.5 --host-weight max_travel_hours=0.3 --host-weight gini_travel_hours=0.2
```

## Output overview

The CLI prints a JSON blob containing the chosen host location, aggregated emissions and travel stats, per-office itineraries, and any requested alternatives. Capture the output with `> result.json` if you need to store it for evaluation.
