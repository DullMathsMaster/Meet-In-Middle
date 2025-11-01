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
    
    def _load_candidate_cities(self) -> Dict[str, Location]:
        """Load candidate meeting cities."""
        # Major international cities that could host meetings
        candidates = {
            "New York": Location("New York", 40.7128, -74.0060, "NYC"),
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
            "Chicago": Location("Chicago", 41.8781, -87.6298, "ORD"),
            "Toronto": Location("Toronto", 43.6532, -79.3832, "YYZ"),
            "Berlin": Location("Berlin", 52.5200, 13.4050, "BER"),
            "Barcelona": Location("Barcelona", 41.3851, 2.1734, "BCN"),
            "Istanbul": Location("Istanbul", 41.0082, 28.9784, "IST"),
            "Bangkok": Location("Bangkok", 13.7563, 100.5018, "BKK"),
            "Seoul": Location("Seoul", 37.5665, 126.9780, "ICN"),
        }
        return candidates
    
    def calculate_distance(self, loc1: Location, loc2: Location) -> float:
        """Calculate great circle distance between two locations (km)."""
        R = 6371  # Earth radius in km
        lat1, lon1 = math.radians(loc1.lat), math.radians(loc1.lon)
        lat2, lon2 = math.radians(loc2.lat), math.radians(loc2.lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
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
    
    def find_travel_options(self, from_loc: str, to_loc: str, 
                           availability_start: datetime, 
                           availability_end: datetime) -> List[TravelOption]:
        """
        Find travel options between two locations within availability window.
        Returns list of TravelOption objects.
        """
        options = []
        
        if from_loc not in self.office_locations or to_loc not in self.candidate_cities:
            return options
        
        from_location = self.office_locations[from_loc]
        to_location = self.candidate_cities[to_loc]
        
        distance = self.calculate_distance(from_location, to_location)
        
        # Generate multiple flight options across the availability window
        current_time = availability_start
        while current_time < availability_end - timedelta(hours=24):
            # Outbound flight
            flight_time = self.estimate_flight_time(distance)
            departure = current_time + timedelta(hours=6)  # Morning departure
            arrival = departure + timedelta(hours=flight_time)
            
            if arrival < availability_end:
                co2 = self.estimate_co2(distance)
                options.append(TravelOption(
                    from_location=from_loc,
                    to_location=to_loc,
                    departure_time=departure,
                    arrival_time=arrival,
                    co2_per_passenger=co2,
                    mode='flight'
                ))
            
            current_time += timedelta(days=1)
        
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
                    co2 = self.estimate_co2(distance, num_attendees)
                    
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
            
            # Normalize scores for comparison (lower is better)
            max_possible_co2 = total_co2 * 2  # Estimate
            max_possible_fairness = fairness_score * 2  # Estimate
            
            normalized_co2 = (total_co2 / max_possible_co2) if max_possible_co2 > 0 else 0
            normalized_fairness = (fairness_score / max_possible_fairness) if max_possible_fairness > 0 else 0
            
            # Combined score (lower is better)
            combined_score = (co2_weight * normalized_co2 + fairness_weight * normalized_fairness)
            
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
            
            solutions.append((combined_score, solution))
        
        # Sort by combined score and return top N
        solutions.sort(key=lambda x: x[0])
        return [sol[1] for sol in solutions[:top_n]]
    
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

