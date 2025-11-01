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

        # Primary detailed emissions file format (emissions.csv)
        flights_dict = {}
        if set(["DEPARTURE_AIRPORT", "ARRIVAL_AIRPORT", "SCHEDULED_DEPARTURE_DATE", "ESTIMATED_CO2_TOTAL_TONNES", "SEATS"]).issubset(set(df.columns)):
            # Compute per passenger CO2 and normalize units to kilograms per passenger
            # ESTIMATED_CO2_TOTAL_TONNES is the total emissions for the aircraft (tonnes).
            # Convert to kg and divide by seats to get per-passenger kg.
            df = df.with_columns(
                ((pl.col("ESTIMATED_CO2_TOTAL_TONNES") * 1000.0) / pl.col("SEATS")).alias("CO2_PER_PAX_KG")
            )

            # Reduce to useful columns
            df = df.select([
                "DEPARTURE_AIRPORT",
                "ARRIVAL_AIRPORT",
                "SCHEDULED_DEPARTURE_DATE",
                "CO2_PER_PAX_KG"
            ])

            # Convert to dictionary for your optimizer
            # flights_dict[origin][destination][date] = CO2 per pax (kg)
            for row in df.iter_rows(named=True):
                origin = row['DEPARTURE_AIRPORT']
                dest = row['ARRIVAL_AIRPORT']
                date = row['SCHEDULED_DEPARTURE_DATE']
                co2 = row['CO2_PER_PAX_KG']

                flights_dict.setdefault(origin, {}).setdefault(dest, {})[date] = co2

        # Additionally, try to load route-level average CO2 dataset if present in datasets/
        avg_map = {}
        try:
            avg_path = csv_path.parent / "datasets" / "average_co2_by_route.csv"
            if avg_path.exists():
                avg_df = pl.read_csv(str(avg_path))
                # Prefer a pre-computed per-person kg column, fall back to tonnes->per-passenger conversion
                if 'ROUTE' in avg_df.columns:
                    AVG_SEATS = 150  # fallback assumption when only per-flight tonnes is provided
                    for row in avg_df.iter_rows(named=True):
                        route = row.get('ROUTE')
                        if not route or '-' not in route:
                            continue
                        origin, dest = route.split('-', 1)

                        per_pax_kg = None
                        # Check for an explicit per-person kg column
                        if 'AVERAGE_CO2_PER_PERSON_KG' in avg_df.columns:
                            try:
                                per_pax_kg = float(row.get('AVERAGE_CO2_PER_PERSON_KG'))
                            except Exception:
                                per_pax_kg = None

                        # If not present, try converting from average tonnes (per flight) -> per pax kg
                        if per_pax_kg is None and 'AVERAGE_CO2_TONNES' in avg_df.columns:
                            try:
                                avg_tonnes = float(row.get('AVERAGE_CO2_TONNES'))
                                per_pax_kg = (avg_tonnes * 1000.0) / AVG_SEATS
                            except Exception:
                                per_pax_kg = None

                        if per_pax_kg is not None:
                            entry = {'AVERAGE': per_pax_kg}
                            # If the CSV contains the per-flight tonnes, include the per-flight kg value too
                            if 'AVERAGE_CO2_TONNES' in avg_df.columns:
                                try:
                                    avg_tonnes = float(row.get('AVERAGE_CO2_TONNES'))
                                    entry['PER_FLIGHT_KG'] = avg_tonnes * 1000.0
                                except Exception:
                                    pass
                            avg_map.setdefault(origin, {}).setdefault(dest, {}).update(entry)
        except Exception:
            # quietly ignore missing/parse errors for average dataset
            avg_map = {}

        # Load airports coordinates mapping (iata -> (lat, lon)) to support distance lookups
        airports_coords = {}
        try:
            airports_path = csv_path.parent / "datasets" / "airports_with_iata.csv"
            if airports_path.exists():
                a_df = pl.read_csv(str(airports_path))
                # Columns expected: iata_code, latitude_deg, longitude_deg
                for row in a_df.iter_rows(named=True):
                    iata = row.get('iata_code') or row.get('IATA_CODE')
                    lat = row.get('latitude_deg')
                    lon = row.get('longitude_deg')
                    if iata and lat is not None and lon is not None and str(iata).strip():
                        airports_coords[str(iata).strip()] = (float(lat), float(lon))
        except Exception:
            airports_coords = {}

        return {
            "flights": flights_dict,
            "co2_emissions": flights_dict,
            "average_co2": avg_map,
            "airports_coords": airports_coords,
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

