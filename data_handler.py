"""
Data handling for JSON input/output and travel data management.
"""
import json
from pathlib import Path
from typing import Dict, List

from algorithm import Location, MeetingOptimizer


def load_office_locations() -> Dict[str, Location]:
    """Load office locations from configuration."""
    # Extended list of major global cities and capitals (name -> Location)
    # These are common meeting hubs; lat/lon are approximate and code is a major IATA for the city.
    offices = {
        # North America
        "New York": Location("New York", 40.6413, -73.7781, "JFK"),
        "Los Angeles": Location("Los Angeles", 33.9416, -118.4085, "LAX"),
        "Chicago": Location("Chicago", 41.9742, -87.9073, "ORD"),
        "Toronto": Location("Toronto", 43.6777, -79.6248, "YYZ"),
        "Vancouver": Location("Vancouver", 49.1947, -123.1790, "YVR"),
        "Mexico City": Location("Mexico City", 19.4361, -99.0719, "MEX"),
        "Washington": Location("Washington", 38.9541, -77.4565, "IAD"),
        "Boston": Location("Boston", 42.3656, -71.0096, "BOS"),
        "Atlanta": Location("Atlanta", 33.6407, -84.4277, "ATL"),

        # South America
        "Sao Paulo": Location("Sao Paulo", -23.6275, -46.6550, "GRU"),
        "Buenos Aires": Location("Buenos Aires", -34.8222, -58.5358, "EZE"),
        "Santiago": Location("Santiago", -33.3930, -70.7858, "SCL"),
        "Lima": Location("Lima", -12.0219, -77.1143, "LIM"),
        "Bogota": Location("Bogota", 4.7016, -74.1469, "BOG"),

        # Europe
        "London": Location("London", 51.4700, -0.4543, "LHR"),
        "Paris": Location("Paris", 49.0097, 2.5479, "CDG"),
        "Frankfurt": Location("Frankfurt", 50.0379, 8.5622, "FRA"),
        "Amsterdam": Location("Amsterdam", 52.3105, 4.7683, "AMS"),
        "Madrid": Location("Madrid", 40.4983, -3.5676, "MAD"),
        "Barcelona": Location("Barcelona", 41.2971, 2.0785, "BCN"),
        "Rome": Location("Rome", 41.7999, 12.2462, "FCO"),
        "Milan": Location("Milan", 45.4642, 9.1900, "MXP"),
        "Berlin": Location("Berlin", 52.3667, 13.5033, "BER"),
        "Zurich": Location("Zurich", 47.4581, 8.5554, "ZRH"),
        "Vienna": Location("Vienna", 48.1103, 16.5697, "VIE"),
        "Dublin": Location("Dublin", 53.4213, -6.2701, "DUB"),
        "Stockholm": Location("Stockholm", 59.6498, 17.9239, "ARN"),
        "Copenhagen": Location("Copenhagen", 55.6181, 12.6561, "CPH"),
        "Oslo": Location("Oslo", 60.1939, 11.1004, "OSL"),
        "Helsinki": Location("Helsinki", 60.3172, 24.9633, "HEL"),
        "Brussels": Location("Brussels", 50.9010, 4.4844, "BRU"),
        "Lisbon": Location("Lisbon", 38.7742, -9.1342, "LIS"),
        "Istanbul": Location("Istanbul", 41.2753, 28.7519, "IST"),

        # Africa
        "Johannesburg": Location("Johannesburg", -26.1392, 28.2460, "JNB"),
        "Cape Town": Location("Cape Town", -33.9706, 18.6021, "CPT"),
        "Nairobi": Location("Nairobi", -1.3192, 36.9278, "NBO"),
        "Lagos": Location("Lagos", 6.5774, 3.3212, "LOS"),
        "Cairo": Location("Cairo", 30.1120, 31.4004, "CAI"),

        # Middle East
        "Dubai": Location("Dubai", 25.2532, 55.3657, "DXB"),
        "Doha": Location("Doha", 25.2731, 51.6080, "DOH"),
        "Riyadh": Location("Riyadh", 24.9576, 46.6980, "RUH"),
        "Tel Aviv": Location("Tel Aviv", 32.0110, 34.8866, "TLV"),

        # Asia
        "Tokyo": Location("Tokyo", 35.6895, 139.6917, "NRT"),
        "Osaka": Location("Osaka", 34.4347, 135.2441, "KIX"),
        "Hong Kong": Location("Hong Kong", 22.3080, 113.9185, "HKG"),
        "Singapore": Location("Singapore", 1.3644, 103.9915, "SIN"),
        "Shanghai": Location("Shanghai", 31.1443, 121.8083, "PVG"),
        "Beijing": Location("Beijing", 40.0799, 116.6031, "PEK"),
        "Seoul": Location("Seoul", 37.4602, 126.4407, "ICN"),
        "Delhi": Location("Delhi", 28.5562, 77.1000, "DEL"),
        "Mumbai": Location("Mumbai", 19.0896, 72.8656, "BOM"),
        "Bangalore": Location("Bangalore", 13.1986, 77.7066, "BLR"),
        "Chennai": Location("Chennai", 12.9946, 80.1709, "MAA"),
        "Jakarta": Location("Jakarta", -6.1264, 106.6604, "CGK"),
        "Kuala Lumpur": Location("Kuala Lumpur", 2.7456, 101.7072, "KUL"),
        "Bangkok": Location("Bangkok", 13.689999, 100.7501, "BKK"),
        "Manila": Location("Manila", 14.5086, 121.0198, "MNL"),

        # Oceania
        "Sydney": Location("Sydney", -33.9399, 151.1753, "SYD"),
        "Melbourne": Location("Melbourne", -37.6690, 144.8410, "MEL"),
        "Auckland": Location("Auckland", -37.0082, 174.7850, "AKL"),
        "Brisbane": Location("Brisbane", -27.3842, 153.1175, "BNE"),
        "Perth": Location("Perth", -31.9403, 115.9678, "PER"),
    }
    return offices


try:
    import polars as pl
    _PL_AVAILABLE = True
except Exception:
    import pandas as pl  # type: ignore
    _PL_AVAILABLE = False

def load_travel_data(file_path: str = "emissions.csv") -> dict:
    """
    Load travel data from emissions.csv
    """
    try:
        data_dir = Path(__file__).resolve().parent
        csv_path = Path(file_path)
        if not csv_path.is_absolute():
            csv_path = data_dir / csv_path

        # Read CSV using polars when available, otherwise pandas
        if _PL_AVAILABLE:
            df = pl.read_csv(str(csv_path))
        else:
            df = pl.read_csv(str(csv_path))

        # Primary detailed emissions file format (emissions.csv)
        flights_dict = {}
        # Support both polars and pandas DataFrame APIs
        cols = set(df.columns)
        if set(["DEPARTURE_AIRPORT", "ARRIVAL_AIRPORT", "SCHEDULED_DEPARTURE_DATE", "ESTIMATED_CO2_TOTAL_TONNES", "SEATS"]).issubset(cols):
            if _PL_AVAILABLE:
                # Compute per passenger CO2 and normalize units to kilograms per passenger
                df = df.with_columns(
                    ((pl.col("ESTIMATED_CO2_TOTAL_TONNES") * 1000.0) / pl.col("SEATS")).alias("CO2_PER_PAX_KG")
                )
                df = df.select([
                    "DEPARTURE_AIRPORT",
                    "ARRIVAL_AIRPORT",
                    "SCHEDULED_DEPARTURE_DATE",
                    "CO2_PER_PAX_KG"
                ])
                for row in df.iter_rows(named=True):
                    origin = row['DEPARTURE_AIRPORT']
                    dest = row['ARRIVAL_AIRPORT']
                    date = row['SCHEDULED_DEPARTURE_DATE']
                    co2 = row['CO2_PER_PAX_KG']
                    flights_dict.setdefault(origin, {}).setdefault(dest, {})[date] = co2
            else:
                # pandas path
                # compute per pax kg
                df['CO2_PER_PAX_KG'] = (df['ESTIMATED_CO2_TOTAL_TONNES'].astype(float) * 1000.0) / df['SEATS'].astype(float)
                for _, row in df.iterrows():
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


def find_city_location(city_name: str) -> Location:
    """
    Try to find a city in datasets/worldcities.csv by exact (case-insensitive)
    match on 'city' or 'city_ascii'. If multiple matches exist, prefer the
    entry with the largest population. Returns a Location object with an
    empty airport code (IATA) if found. Raises ValueError if not found.
    """
    data_dir = Path(__file__).resolve().parent
    wc_path = data_dir / 'datasets' / 'worldcities.csv'
    airports_path = data_dir / 'datasets' / 'airports_with_iata.csv'
    airports_all_path = data_dir / 'datasets' / 'airports.csv'
    if not wc_path.exists():
        raise FileNotFoundError(f"worldcities.csv not found at {wc_path}")

    try:
        wc = pl.read_csv(str(wc_path))
    except Exception as e:
        raise RuntimeError(f"Failed to read worldcities.csv: {e}")

    # Load airports table(s) if available to try to find nearest airport / direct IATA lookups
    airports_df = None
    airports_all_df = None
    try:
        if airports_path.exists():
            airports_df = pl.read_csv(str(airports_path))
    except Exception:
        airports_df = None
    try:
        if airports_all_path.exists():
            airports_all_df = pl.read_csv(str(airports_all_path))
    except Exception:
        airports_all_df = None

    # normalize name comparisons
    cname = city_name.strip().lower()
    # exact matches on city or city_ascii
    def match_row(r):
        c1 = (r.get('city') or '').strip().lower()
        c2 = (r.get('city_ascii') or '').strip().lower()
        return c1 == cname or c2 == cname

    matches = [row for row in wc.iter_rows(named=True) if match_row(row)]

    # If no exact match, try startswith or contains heuristics
    if not matches:
        matches = [row for row in wc.iter_rows(named=True)
                   if (row.get('city') or '').strip().lower().startswith(cname) or
                      (row.get('city_ascii') or '').strip().lower().startswith(cname)]

    if not matches:
        matches = [row for row in wc.iter_rows(named=True)
                   if cname in ((row.get('city') or '') + ' ' + (row.get('city_ascii') or '')).lower()]

    if not matches:
        raise ValueError(f"City '{city_name}' not found in worldcities.csv")

    # prefer highest population if present
    def pop_val(r):
        try:
            return float(r.get('population') or 0)
        except Exception:
            return 0

    best = max(matches, key=pop_val)
    lat = float(best.get('lat'))
    lon = float(best.get('lng') or best.get('lon') or 0)

    # If the input looks like an IATA code (3 letters) and airports dataset is present,
    # prefer returning that airport directly.
    try_iata = city_name.strip().upper()
    if airports_df is not None and len(try_iata) == 3:
        # try direct match on iata_code or IATA_CODE
        for row in airports_df.iter_rows(named=True):
            iata = (row.get('iata_code') or row.get('IATA_CODE') or '').strip()
            if iata.upper() == try_iata:
                ap_lat = float(row.get('latitude_deg'))
                ap_lon = float(row.get('longitude_deg'))
                ap_name = row.get('name') or row.get('airport_name') or try_iata
                return Location(ap_name, ap_lat, ap_lon, try_iata)

    # If user provided a city (not an IATA) try to find an airport in airports.csv
    # whose 'municipality' matches the city name (case-insensitive). Prefer
    # airports with non-empty IATA codes.
    cname_normal = city_name.strip().lower()
    if airports_all_df is not None:
        candidates = []
        for row in airports_all_df.iter_rows(named=True):
            muni = (row.get('municipality') or '').strip().lower()
            name = (row.get('name') or '').strip().lower()
            iata = (row.get('iata_code') or row.get('IATA_CODE') or '').strip()
            if muni == cname_normal or name == cname_normal or cname_normal in name:
                # ensure coordinates exist
                latv = row.get('latitude_deg')
                lonv = row.get('longitude_deg')
                if latv is None or lonv is None:
                    continue
                candidates.append((row, iata, float(latv), float(lonv)))

        # prefer candidates that have an IATA code
        if candidates:
            with_iata = [c for c in candidates if c[1]]
            pick = with_iata[0] if with_iata else candidates[0]
            r, iata, ap_lat, ap_lon = pick
            ap_name = r.get('name') or city_name
            return Location(ap_name, ap_lat, ap_lon, iata)

    # Otherwise, attempt to find the nearest airport to the city coordinates (within 150 km)
    selected_iata = ""
    if airports_df is not None:
        # helper: haversine
        import math
        def haversine_km(lat1, lon1, lat2, lon2):
            R = 6371.0
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            # Normalize longitude difference to the shorter path across the dateline
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            dlambda = (dlambda + math.pi) % (2 * math.pi) - math.pi
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
            return R * 2 * math.asin(math.sqrt(a))

        best_airport = None
        best_dist = None
        for row in airports_df.iter_rows(named=True):
            try:
                ap_lat = float(row.get('latitude_deg'))
                ap_lon = float(row.get('longitude_deg'))
            except Exception:
                continue
            d = haversine_km(lat, lon, ap_lat, ap_lon)
            if best_dist is None or d < best_dist:
                best_dist = d
                best_airport = row

        if best_airport is not None and best_dist is not None and best_dist <= 150:
            iata = (best_airport.get('iata_code') or best_airport.get('IATA_CODE') or '').strip()
            if iata:
                selected_iata = iata

    # return Location, include IATA if we found a nearby airport
    return Location(str(best.get('city') or city_name), lat, lon, selected_iata)

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

