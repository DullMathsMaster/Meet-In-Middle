"""
Data handling for JSON input/output and travel data management.
"""
import json
from pathlib import Path
from typing import Dict, List

from algorithm import Location, MeetingOptimizer


def load_office_locations() -> Dict[str, Location]:
    """Load office locations from configuration."""
    # Major office locations - can be extended
    offices = {
        "Mumbai": Location("Mumbai", 19.0760, 72.8777, "BOM"),
        "Shanghai": Location("Shanghai", 31.2304, 121.4737, "PVG"),
        "Hong Kong": Location("Hong Kong", 22.3193, 114.1694, "HKG"),
        "Singapore": Location("Singapore", 1.3521, 103.8198, "SIN"),
        "Sydney": Location("Sydney", -33.8688, 151.2093, "SYD"),
        "London": Location("London", 51.5074, -0.1278, "LHR"),
        "New York": Location("New York", 40.7128, -74.0060, "NYC"),
        "Tokyo": Location("Tokyo", 35.6762, 139.6503, "NRT"),
        "Berlin": Location("Berlin", 52.5200, 13.4050, "BER"),
        "Dubai": Location("Dubai", 25.2048, 55.2708, "DXB"),
        "Paris": Location("Paris", 48.8566, 2.3522, "CDG"),
        "Los Angeles": Location("Los Angeles", 34.0522, -118.2437, "LAX"),
    }
    return offices


import polars as pl

def load_travel_data(file_path: str = "emissions.csv") -> dict:
    """
    Load travel data from emissions.csv
    """
    try:
        data_dir = Path(__file__).resolve().parent
        csv_path = Path(file_path)
        if not csv_path.is_absolute():
            csv_path = data_dir / csv_path

        df = pl.read_csv(str(csv_path))
        # Compute per passenger CO2
        df = df.with_columns(
            (pl.col("ESTIMATED_CO2_TOTAL_TONNES") / pl.col("SEATS")).alias("CO2_PER_PAX_TONNES")
        )

        # Reduce to useful columns
        df = df.select([
            "DEPARTURE_AIRPORT",
            "ARRIVAL_AIRPORT",
            "SCHEDULED_DEPARTURE_DATE",
            "CO2_PER_PAX_TONNES"
        ])

        # Convert to dictionary for your optimizer
        # flights_dict[origin][destination][date] = CO2 per pax
        flights_dict = {}
        for row in df.iter_rows(named=True):
            origin = row['DEPARTURE_AIRPORT']
            dest = row['ARRIVAL_AIRPORT']
            date = row['SCHEDULED_DEPARTURE_DATE']
            co2 = row['CO2_PER_PAX_TONNES']

            flights_dict.setdefault(origin, {}).setdefault(dest, {})[date] = co2

        return {
            "flights": flights_dict,
            "co2_emissions": flights_dict
        }

    except FileNotFoundError:
        print(f"Error: {csv_path} not found")
        return {
            "flights": {},
            "co2_emissions": {}
        }

def parse_input_json(input_data: Dict) -> Dict:
    """
    Parse input JSON and validate structure.
    
    Expected format:
    {
        "attendees": {"Office": count, ...},
        "availability_window": {"start": "ISO datetime", "end": "ISO datetime"},
        "event_duration": {"days": int, "hours": int}
    }
    """
    required_keys = ['attendees', 'availability_window', 'event_duration']
    
    for key in required_keys:
        if key not in input_data:
            raise ValueError(f"Missing required key: {key}")
    
    # Validate attendees
    if not isinstance(input_data['attendees'], dict):
        raise ValueError("'attendees' must be a dictionary")
    
    # Validate availability window
    window = input_data['availability_window']
    if 'start' not in window or 'end' not in window:
        raise ValueError("'availability_window' must contain 'start' and 'end'")
    
    # Validate event duration
    duration = input_data['event_duration']
    if 'days' not in duration or 'hours' not in duration:
        raise ValueError("'event_duration' must contain 'days' and 'hours'")
    
    return input_data


def load_input_from_file(file_path: str) -> Dict:
    """Load and parse input JSON from file."""
    data_dir = Path(__file__).resolve().parent
    json_path = Path(file_path)
    if not json_path.is_absolute():
        json_path = data_dir / json_path

    with open(json_path, 'r') as f:
        data = json.load(f)
    return parse_input_json(data)


def save_output_json(output_data: Dict, file_path: str):
    """Save output JSON to file."""
    output_dir = Path(file_path)
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    with open(output_dir, 'w') as f:
        json.dump(output_data, f, indent=2)


def create_comparison_output(solutions: List[Dict]) -> Dict:
    """Create comparison output with multiple candidate cities."""
    if not solutions:
        return {}
    
    best = solutions[0]
    
    comparison = {
        "best_solution": best,
        "alternatives": solutions[1:5] if len(solutions) > 1 else [],
        "comparison_metrics": {
            "cities_evaluated": len(solutions),
            "co2_range": {
                "min": min(s['total_co2'] for s in solutions),
                "max": max(s['total_co2'] for s in solutions),
                "avg": sum(s['total_co2'] for s in solutions) / len(solutions)
            },
            "travel_time_range": {
                "min_avg": min(s['average_travel_hours'] for s in solutions),
                "max_avg": max(s['average_travel_hours'] for s in solutions),
                "avg_avg": sum(s['average_travel_hours'] for s in solutions) / len(solutions)
            },
            "fairness_range": {
                "min": min(s.get('fairness_score', 0) for s in solutions),
                "max": max(s.get('fairness_score', 0) for s in solutions),
                "avg": sum(s.get('fairness_score', 0) for s in solutions) / len(solutions)
            }
        }
    }
    
    return comparison

