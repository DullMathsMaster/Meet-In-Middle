"""
Core algorithm for optimizing meeting location based on CO2 emissions and fairness.
"""
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Location:
    """Represents a geographic location."""
    name: str
    lat: float
    lon: float
    code: str  # Airport/IATA code


@dataclass
class TravelOption:
    """Represents a travel option between two locations."""
    from_location: str
    to_location: str
    departure_time: datetime
    arrival_time: datetime
    co2_per_passenger: float
    mode: str  # 'flight', 'train', etc.


@dataclass
class AttendeeTravel:
    """Represents travel details for an attendee from a location."""
    location: str
    outbound: Optional[TravelOption]
    return_trip: Optional[TravelOption]
    total_hours: float
    total_co2: float


@dataclass
class Solution:
    """Represents a meeting location solution."""
    location: str
    event_dates: Dict[str, str]
    event_span: Dict[str, str]
    total_co2: float
    average_travel_hours: float
    median_travel_hours: float
    max_travel_hours: float
    min_travel_hours: float
    attendee_travel_hours: Dict[str, float]
    fairness_score: float
    attendee_details: Dict[str, AttendeeTravel]


class MeetingOptimizer:
    """Optimizes meeting location balancing CO2 emissions and travel fairness."""
    def __init__(self, travel_data: Dict, office_locations: Dict[str, Location]):
        """
        Initialize optimizer with travel data and office locations.
        
        Args:
            travel_data: Dictionary containing flight schedules and CO2 data
            office_locations: Dictionary mapping office names to Location objects
        """
        self.travel_data = travel_data
        self.office_locations = office_locations
        self.candidate_cities = self._load_candidate_cities()
        # If travel_data provides airport coordinates, validate candidate IATA codes
        try:
            self._check_candidate_iata()
        except Exception:
            # don't raise during init; validation is best-effort
            pass
    
    def _load_candidate_cities(self) -> Dict[str, Location]:
        """Load candidate meeting cities."""
        # Major international cities that could host meetings
        candidates = {
            "New York": Location("New York", 40.7128, -74.0060, "JFK"),
            "London": Location("London", 51.5074, -0.1278, "LHR"),
            "Singapore": Location("Singapore", 1.3521, 103.8198, "SIN"),
            "Dubai": Location("Dubai", 25.2048, 55.2708, "DXB"),
            "Tokyo": Location("Tokyo", 35.6762, 139.6503, "NRT"),
            "Frankfurt": Location("Frankfurt", 50.1109, 8.6821, "FRA"),
            "Paris": Location("Paris", 48.8566, 2.3522, "CDG"),
            "Amsterdam": Location("Amsterdam", 52.3676, 4.9041, "AMS"),
            "Hong Kong": Location("Hong Kong", 22.3193, 114.1694, "HKG"),
            "Sydney": Location("Sydney", -33.8688, 151.2093, "SYD"),
            "Mumbai": Location("Mumbai", 19.0760, 72.8777, "BOM"),
            "Shanghai": Location("Shanghai", 31.2304, 121.4737, "PVG"),
            "Los Angeles": Location("Los Angeles", 34.0522, -118.2437, "LAX"),
            "San Francisco": Location("San Francisco", 37.7749, -122.4194, "SFO"),
            "Chicago": Location("Chicago", 41.8781, -87.6298, "ORD"),
            "Toronto": Location("Toronto", 43.6532, -79.3832, "YYZ"),
            "Berlin": Location("Berlin", 52.5200, 13.4050, "BER"),
            "Barcelona": Location("Barcelona", 41.3851, 2.1734, "BCN"),
            "Madrid": Location("Madrid", 40.4168, -3.7038, "MAD"),
            "Rome": Location("Rome", 41.9028, 12.4964, "FCO"),
            "Istanbul": Location("Istanbul", 41.0082, 28.9784, "IST"),
            "Athens": Location("Athens", 37.9838, 23.7275, "ATH"),
            "Stockholm": Location("Stockholm", 59.3293, 18.0686, "ARN"),
            "Oslo": Location("Oslo", 59.9139, 10.7522, "OSL"),
            "Helsinki": Location("Helsinki", 60.1699, 24.9384, "HEL"),
            "Copenhagen": Location("Copenhagen", 55.6761, 12.5683, "CPH"),
            "Zurich": Location("Zurich", 47.3769, 8.5417, "ZRH"),
            "Brussels": Location("Brussels", 50.8503, 4.3517, "BRU"),
            "Vienna": Location("Vienna", 48.2082, 16.3738, "VIE"),
            "Warsaw": Location("Warsaw", 52.2297, 21.0122, "WAW"),
            "Prague": Location("Prague", 50.0755, 14.4378, "PRG"),
            "Budapest": Location("Budapest", 47.4979, 19.0402, "BUD"),
            "Moscow": Location("Moscow", 55.7558, 37.6176, "SVO"),
            "Seoul": Location("Seoul", 37.5665, 126.9780, "ICN"),
            "Beijing": Location("Beijing", 39.9042, 116.4074, "PEK"),
            "Bangkok": Location("Bangkok", 13.7563, 100.5018, "BKK"),
            "Kuala Lumpur": Location("Kuala Lumpur", 3.1390, 101.6869, "KUL"),
            "Jakarta": Location("Jakarta", -6.2088, 106.8456, "CGK"),
            "Manila": Location("Manila", 14.5995, 120.9842, "MNL"),
            "Ho Chi Minh City": Location("Ho Chi Minh City", 10.8231, 106.6297, "SGN"),
            "Delhi": Location("Delhi", 28.7041, 77.1025, "DEL"),
            "Bangalore": Location("Bangalore", 12.9716, 77.5946, "BLR"),
            "Chennai": Location("Chennai", 13.0827, 80.2707, "MAA"),
            "Sao Paulo": Location("Sao Paulo", -23.5505, -46.6333, "GRU"),
            "Rio de Janeiro": Location("Rio de Janeiro", -22.9068, -43.1729, "GIG"),
            "Buenos Aires": Location("Buenos Aires", -34.6037, -58.3816, "EZE"),
            "Mexico City": Location("Mexico City", 19.4326, -99.1332, "MEX"),
            "Lima": Location("Lima", -12.0464, -77.0428, "LIM"),
            "Bogota": Location("Bogota", 4.7110, -74.0721, "BOG"),
            "Santiago": Location("Santiago", -33.4489, -70.6693, "SCL"),
            "Johannesburg": Location("Johannesburg", -26.2041, 28.0473, "JNB"),
            "Cape Town": Location("Cape Town", -33.9249, 18.4241, "CPT"),
            "Nairobi": Location("Nairobi", -1.2921, 36.8219, "NBO"),
            "Cairo": Location("Cairo", 30.0444, 31.2357, "CAI"),
            "Tehran": Location("Tehran", 35.6892, 51.3890, "IKA"),
            "Riyadh": Location("Riyadh", 24.7136, 46.6753, "RUH"),
        }
        return candidates

    def _check_candidate_iata(self):
        """Best-effort check that candidate city IATA codes exist in travel_data airports map.

        Prints a short summary of any missing codes so you can update candidates or the airports dataset.
        """
        airports_coords = self.travel_data.get('airports_coords', {}) if isinstance(self.travel_data, dict) else {}
        if not airports_coords:
            print("[info] No airports_coords found in travel_data; skipping candidate IATA validation.")
            return

        missing = []
        for city, loc in self.candidate_cities.items():
            code = (loc.code or '').strip()
            if not code:
                missing.append((city, code))
            elif code not in airports_coords:
                missing.append((city, code))

        if not missing:
            print(f"[info] All {len(self.candidate_cities)} candidate IATA codes found in airports dataset.")
        else:
            print(f"[warning] {len(missing)} candidate IATA codes were NOT found in airports dataset. Sample:")
            for city, code in missing[:20]:
                print(f"  - {city}: '{code}'")
            print("If codes are missing, either update the candidate code or add the airport to datasets/airports_with_iata.csv")
    
    def calculate_distance(self, loc1: Location, loc2: Location) -> float:
        """Calculate great circle distance between two locations (km)."""
        R = 6371  # Earth radius in km
        lat1, lon1 = math.radians(loc1.lat), math.radians(loc1.lon)
        lat2, lon2 = math.radians(loc2.lat), math.radians(loc2.lon)
        # Use the shortest longitudinal difference (normalize to [-pi, pi]) to avoid
        # choosing the long way around the globe when longitudes cross the antimeridian.
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        dlon = (dlon + math.pi) % (2 * math.pi) - math.pi

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c

    def get_co2_value(self, from_iata: str, to_iata: str, date: Optional[str] = None,
                      per_person: bool = True, avg_seats: int = 150) -> Optional[float]:
        """
        Return CO2 either per person (kg) or per flight (kg) for a given route.

        Lookup order:
        1. If a date is provided and a dated detailed flight exists, use that (stored as kg/pax).
        2. If route-level averages exist in travel_data['average_co2'], prefer explicit per-person kg.
           If per-flight kg is available in the averages data, use that when per_person=False.
        3. If none of the above, estimate using distance and the estimator (returns kg/pax),
           and convert to per-flight by multiplying by avg_seats if requested.

        Returns kg (per person if per_person=True, otherwise per flight total kg). Returns None
        only if route can't be resolved and distance can't be estimated.
        """
        td = self.travel_data or {}

        # 1) dated detailed flight (kg per pax)
        if date:
            dated = td.get('co2_emissions', {}).get(from_iata, {}).get(to_iata, {})
            if isinstance(dated, dict) and date in dated:
                per_pax = dated[date]
                if per_person:
                    return per_pax
                else:
                    return per_pax * avg_seats

        # 2) averages
        avg_entry = td.get('average_co2', {}).get(from_iata, {}).get(to_iata, {})
        if not avg_entry:
            # try reverse direction
            avg_entry = td.get('average_co2', {}).get(to_iata, {}).get(from_iata, {})

        if avg_entry:
            per_pax = avg_entry.get('AVERAGE')
            per_flight = avg_entry.get('PER_FLIGHT_KG')
            if per_pax is not None:
                if per_person:
                    return per_pax
                else:
                    if per_flight is not None:
                        return per_flight
                    else:
                        return per_pax * avg_seats

        # 3) fallback: estimate from distance
        # Try to get coordinates
        origin_loc = None
        dest_loc = None
        # Check office locations and candidate cities
        for name, loc in self.office_locations.items():
            if (loc.code or '').strip() == from_iata:
                origin_loc = loc
                break
        for name, loc in self.candidate_cities.items():
            if (loc.code or '').strip() == to_iata:
                dest_loc = loc
                break

        if origin_loc is None or dest_loc is None:
            airports_coords = td.get('airports_coords', {})
            origin_coords = airports_coords.get(from_iata)
            dest_coords = airports_coords.get(to_iata)
            if origin_coords and dest_coords:
                origin_loc = Location(from_iata, origin_coords[0], origin_coords[1], from_iata)
                dest_loc = Location(to_iata, dest_coords[0], dest_coords[1], to_iata)

        if origin_loc and dest_loc:
            distance_km = self.calculate_distance(origin_loc, dest_loc)
            per_pax_est = self.estimate_co2(distance_km, passengers=1)
            if per_person:
                return per_pax_est
            else:
                return per_pax_est * avg_seats

        # Nothing found
        return None
    
    def estimate_flight_time(self, distance_km: float) -> float:
        """Estimate flight time in hours based on distance."""
        # Rough estimate: average speed ~900 km/h for long-haul, faster for short
        if distance_km < 1000:
            return distance_km / 700  # Short-haul slower
        elif distance_km < 5000:
            return distance_km / 850
        else:
            return distance_km / 900  # Long-haul
    
    def estimate_co2(self, distance_km: float, passengers: int = 1) -> float:
        """
        Estimate CO2 emissions in kg for a flight.
        Uses average: ~115g CO2 per passenger per km for short-haul,
        ~180g for medium, ~260g for long-haul.
        """


        if distance_km < 1500:
            return distance_km * 0.115 * passengers
        elif distance_km < 4000:
            return distance_km * 0.180 * passengers
        else:
            return distance_km * 0.260 * passengers
    
    def find_travel_options(self, from_loc: str, to_loc: str, availability_start, availability_end):
        options = []
        from_iata = self.office_locations[from_loc].code
        to_iata = self.candidate_cities[to_loc].code

        flight_dict = self.travel_data['co2_emissions'].get(from_iata, {}).get(to_iata, {})
        for date_str, co2 in flight_dict.items():
            flight_date = datetime.fromisoformat(date_str)
            if availability_start <= flight_date <= availability_end:
                options.append(
                    TravelOption(
                        from_location=from_loc,
                        to_location=to_loc,
                        departure_time=flight_date,
                        arrival_time=flight_date + timedelta(hours=self.estimate_flight_time(self.calculate_distance(self.office_locations[from_loc], self.candidate_cities[to_loc]))),
                        co2_per_passenger=co2,
                        mode='flight'
                    )
                )
        # If no date-specific options, try route-level average CO2 (from dataset)
        if not options:
            avg_map = self.travel_data.get('average_co2', {})
            avg_entry = avg_map.get(from_iata, {}).get(to_iata, {}) if avg_map else None
            avg_val = None
            if isinstance(avg_entry, dict):
                avg_val = avg_entry.get('AVERAGE')
            # also try reverse direction (some datasets store DEST-ORIG)
            if avg_val is None:
                rev_entry = avg_map.get(to_iata, {}).get(from_iata, {}) if avg_map else None
                if isinstance(rev_entry, dict):
                    avg_val = rev_entry.get('AVERAGE')

            if avg_val is not None:
                # Determine distance between the two airports/locations
                distance_km = None
                # Prefer office/candidate Location objects
                origin_loc_obj = self.office_locations.get(from_loc)
                dest_loc_obj = self.candidate_cities.get(to_loc)
                if origin_loc_obj and dest_loc_obj:
                    distance_km = self.calculate_distance(origin_loc_obj, dest_loc_obj)
                else:
                    # Fallback to airports coords provided by data_handler
                    airports_coords = self.travel_data.get('airports_coords', {})
                    origin_coords = airports_coords.get(from_iata)
                    dest_coords = airports_coords.get(to_iata)
                    if origin_coords and dest_coords:
                        origin_loc_obj = Location(from_loc, origin_coords[0], origin_coords[1], from_iata)
                        dest_loc_obj = Location(to_loc, dest_coords[0], dest_coords[1], to_iata)
                        distance_km = self.calculate_distance(origin_loc_obj, dest_loc_obj)

                # If we couldn't find coords, still add an option using availability_start
                depart_time = availability_start
                if distance_km is None:
                    est_hours = self.estimate_flight_time(1000)  # fallback estimate
                else:
                    est_hours = self.estimate_flight_time(distance_km)

                options.append(
                    TravelOption(
                        from_location=from_loc,
                        to_location=to_loc,
                        departure_time=depart_time,
                        arrival_time=depart_time + timedelta(hours=est_hours),
                        co2_per_passenger=avg_val,
                        mode='flight'
                    )
                )

        return options

    
    def calculate_fairness_score(self, travel_hours: Dict[str, float]) -> float:
        """
        Calculate fairness score (lower is better).
        Uses coefficient of variation (CV) as fairness metric.
        """
        if not travel_hours:
            return float('inf')
        
        hours_list = list(travel_hours.values())
        if all(h == 0 for h in hours_list):
            return 0.0
        
        mean_hours = sum(hours_list) / len(hours_list)
        if mean_hours == 0:
            return 0.0
        
        variance = sum((h - mean_hours) ** 2 for h in hours_list) / len(hours_list)
        std_dev = math.sqrt(variance)
        coefficient_of_variation = std_dev / mean_hours if mean_hours > 0 else 0
        
        # Also consider max/min ratio
        non_zero_hours = [h for h in hours_list if h > 0]
        if len(non_zero_hours) > 1:
            max_min_ratio = max(non_zero_hours) / min(non_zero_hours)
        else:
            max_min_ratio = 1.0
        
        # Combined fairness score (weighted combination)
        fairness = 0.7 * coefficient_of_variation + 0.3 * (max_min_ratio - 1.0)
        return fairness
    
    def optimize_location(self, attendees: Dict[str, int],
                         availability_window: Dict[str, str],
                         event_duration: Dict[str, int],
                         co2_weight: float = 0.5,
                         fairness_weight: float = 0.5,
                         top_n: int = 5) -> List[Solution]:
        """
        Find optimal meeting locations balancing CO2 and fairness.
        
        Args:
            attendees: Dict mapping office names to number of attendees
            availability_window: Dict with 'start' and 'end' ISO datetime strings
            event_duration: Dict with 'days' and 'hours'
            co2_weight: Weight for CO2 emissions (0-1)
            fairness_weight: Weight for fairness (0-1), should sum to 1 with co2_weight
            top_n: Number of top solutions to return
            
        Returns:
            List of Solution objects sorted by combined score
        """
        # Parse datetime strings, handling Z (UTC) suffix
        start_str = availability_window['start']
        end_str = availability_window['end']
        
        if start_str.endswith('Z'): 
            start_str = start_str[:-1] + '+00:00'
        elif '+' not in start_str and start_str.count(':') >= 2:
            # Assume UTC if no timezone info
            start_str = start_str + '+00:00'
            
        if end_str.endswith('Z'):
            end_str = end_str[:-1] + '+00:00'
        elif '+' not in end_str and end_str.count(':') >= 2:
            end_str = end_str + '+00:00'
        
        start_time = datetime.fromisoformat(start_str)
        end_time = datetime.fromisoformat(end_str)
        outbound_date_str = (start_time + timedelta(hours=6)).date().isoformat()
        
        # Convert to naive datetime for calculations (assume UTC)
        if start_time.tzinfo:
            start_time = start_time.replace(tzinfo=None)
        if end_time.tzinfo:
            end_time = end_time.replace(tzinfo=None)
        
            event_hours = event_duration.get('days', 0) * 24 + event_duration.get('hours', 0)

            solutions = []
        
        # Evaluate each candidate city
        for city_name, city_location in self.candidate_cities.items():
            attendee_travels = {}
            total_co2 = 0
            all_arrival_times = []
            all_departure_times = []
            
            # Calculate travel for each office
            for office_name, num_attendees in attendees.items():
                if office_name == city_name:
                    # Same city - no travel
                    attendee_travels[office_name] = AttendeeTravel(
                        location=office_name,
                        outbound=None,
                        return_trip=None,
                        total_hours=0,
                        total_co2=0
                    )
                    all_arrival_times.append(start_time)
                    all_departure_times.append(end_time)
                    continue
                
                # Find travel options
                travel_options = self.find_travel_options(
                    office_name, city_name, start_time, end_time
                )
                
                if not travel_options:
                    # If no specific flights found, use distance-based estimates
                    office_loc = self.office_locations.get(office_name)
                    if not office_loc:
                        continue
                    
                    distance = self.calculate_distance(office_loc, city_location)
                    flight_hours = self.estimate_flight_time(distance)
                    co2_per_pax = self.travel_data['co2_emissions'].get(self.office_locations[office_name].code, {}).get(city_location.code, {}).get(outbound_date_str, None)
                    
                    if co2_per_pax is not None:
                         co2 = co2_per_pax * num_attendees * 2  # round trip
                    else:
                        co2 = self.estimate_co2(distance, num_attendees)  # fallback
                    
                    # Estimate arrival and departure times
                    outbound_departure = start_time + timedelta(hours=6)
                    outbound_arrival = outbound_departure + timedelta(hours=flight_hours)
                    
                    # Return flight after event
                    return_departure = start_time + timedelta(hours=event_hours + 2)
                    return_arrival = return_departure + timedelta(hours=flight_hours)
                    
                    attendee_travels[office_name] = AttendeeTravel(
                        location=office_name,
                        outbound=TravelOption(
                            from_location=office_name,
                            to_location=city_name,
                            departure_time=outbound_departure,
                            arrival_time=outbound_arrival,
                            co2_per_passenger=co2 / num_attendees,
                            mode='flight'
                        ),
                        return_trip=TravelOption(
                            from_location=city_name,
                            to_location=office_name,
                            departure_time=return_departure,
                            arrival_time=return_arrival,
                            co2_per_passenger=co2 / num_attendees,
                            mode='flight'
                        ),
                        total_hours=flight_hours * 2,
                        total_co2=co2
                    )
                    
                    total_co2 += co2
                    all_arrival_times.append(outbound_arrival)
                    all_departure_times.append(return_arrival)
                else:
                    # Use actual travel options
                    best_option = min(travel_options, key=lambda x: x.co2_per_passenger)
                    travel_hours = (best_option.arrival_time - best_option.departure_time).total_seconds() / 3600
                    co2 = best_option.co2_per_passenger * num_attendees * 2  # Round trip
                    
                    attendee_travels[office_name] = AttendeeTravel(
                        location=office_name,
                        outbound=best_option,
                        return_trip=None,  # Simplified
                        total_hours=travel_hours * 2,
                        total_co2=co2
                    )
                    
                    total_co2 += co2
                    all_arrival_times.append(best_option.arrival_time)
                    all_departure_times.append(best_option.arrival_time + timedelta(hours=event_hours + travel_hours))
            
            if not attendee_travels:
                continue
            
            # Calculate statistics
            travel_hours_dict = {loc: travel.total_hours for loc, travel in attendee_travels.items()}
            hours_list = list(travel_hours_dict.values())
            
            if not hours_list:
                continue
            
            avg_hours = sum(hours_list) / len(hours_list)
            median_hours = sorted(hours_list)[len(hours_list) // 2]
            max_hours = max(hours_list)
            min_hours = min(hours_list)
            
            # Event dates - all attendees must be present
            event_start = max(all_arrival_times) if all_arrival_times else start_time
            event_end = event_start + timedelta(hours=event_hours)
            
            # Event span - first arrival to last departure
            event_span_start = min(all_arrival_times) if all_arrival_times else start_time
            event_span_end = max(all_departure_times) if all_departure_times else end_time
            
            fairness_score = self.calculate_fairness_score(travel_hours_dict)

            # Create Solution object (scoring is applied after evaluating all cities)
            solution = Solution(
                location=city_name,
                event_dates={
                    'start': event_start.isoformat(),
                    'end': event_end.isoformat()
                },
                event_span={
                    'start': event_span_start.isoformat(),
                    'end': event_span_end.isoformat()
                },
                total_co2=total_co2,
                average_travel_hours=avg_hours,
                median_travel_hours=median_hours,
                max_travel_hours=max_hours,
                min_travel_hours=min_hours,
                attendee_travel_hours=travel_hours_dict,
                fairness_score=fairness_score,
                attendee_details=attendee_travels
            )
            
            # Append raw solution with its raw metrics; we'll normalize/sort later
            solutions.append((solution, total_co2, fairness_score))
        
        # If no solutions found, return empty
        if not solutions:
            return []

        # Compute min-max across total_co2 and fairness to normalize
        co2_values = [t[1] for t in solutions]
        fairness_values = [t[2] for t in solutions]
        min_co2, max_co2 = min(co2_values), max(co2_values)
        min_fair, max_fair = min(fairness_values), max(fairness_values)

        scored = []
        for sol_obj, sol_co2, sol_fair in solutions:
            if max_co2 > min_co2:
                norm_co2 = (sol_co2 - min_co2) / (max_co2 - min_co2)
            else:
                norm_co2 = 0.0

            # For fairness higher = worse; normalize so higher -> larger normalized value
            if max_fair > min_fair:
                norm_fair = (sol_fair - min_fair) / (max_fair - min_fair)
            else:
                norm_fair = 0.0

            combined_score = co2_weight * norm_co2 + fairness_weight * norm_fair
            scored.append((combined_score, sol_obj))

        # Sort by combined score (lower is better) and return top N Solution objects
        scored.sort(key=lambda x: x[0])
        return [t[1] for t in scored[:top_n]]
    
    def solution_to_dict(self, solution: Solution) -> Dict:
        """Convert Solution object to dictionary format for JSON output."""
        return {
            "event_location": solution.location,
            "event_dates": solution.event_dates,
            "event_span": solution.event_span,
            "total_co2": round(solution.total_co2, 2),
            "average_travel_hours": round(solution.average_travel_hours, 2),
            "median_travel_hours": round(solution.median_travel_hours, 2),
            "max_travel_hours": round(solution.max_travel_hours, 2),
            "min_travel_hours": round(solution.min_travel_hours, 2),
            "attendee_travel_hours": {k: round(v, 2) for k, v in solution.attendee_travel_hours.items()},
            "fairness_score": round(solution.fairness_score, 4)
        }

