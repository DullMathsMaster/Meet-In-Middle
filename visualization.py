"""
Visualization tools for meeting location optimization results.
"""
import json
from typing import Dict, List, Optional
from pathlib import Path

# Optional import for folium (map visualization)
try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

from algorithm import Solution, Location, AttendeeTravel


def create_map_visualization(solutions: List[Solution], 
                            office_locations: Dict[str, Location],
                            candidate_cities: Dict[str, Location],
                            output_path: str = 'visualization.html'):
    """
    Create an interactive map visualization showing:
    - Office locations
    - Best meeting location
    - Travel paths from offices to meeting location
    """
    if not FOLIUM_AVAILABLE:
        print("Warning: Folium not available. Map visualization skipped.")
        return None
    
    if not solutions:
        return None
    
    best_solution = solutions[0]
    meeting_location = candidate_cities.get(best_solution.location)
    
    if not meeting_location:
        return None
    
    # Create base map centered on meeting location
    m = folium.Map(
        location=[meeting_location.lat, meeting_location.lon],
        zoom_start=3,
        tiles='OpenStreetMap'
    )
    
    # Add meeting location marker
    # If an office has the same name as the meeting location, include its travel info
    same_office_info = []
    for office_name, travel in best_solution.attendee_details.items():
        if office_name == meeting_location.name:
            same_office_info.append(f"<br><b>Office: {office_name}</b><br>Travel Hours: {travel.total_hours:.2f}<br>CO2: {travel.total_co2:.2f} kg")

    meeting_popup = (
        f"<b>Meeting Location: {meeting_location.name}</b><br>"
        f"Total CO2: {best_solution.total_co2:.2f} kg<br>"
        f"Avg Travel: {best_solution.average_travel_hours:.2f} hours<br>"
        f"Fairness Score: {best_solution.fairness_score:.4f}"
    )
    if same_office_info:
        meeting_popup += "<hr>" + "".join(same_office_info)

    # Destination marker should be prominent and red
    folium.Marker(
        [meeting_location.lat, meeting_location.lon],
        popup=meeting_popup,
        tooltip=meeting_location.name,
        icon=folium.Icon(color='red', icon='star', prefix='fa')
    ).add_to(m)
    
    # Add office locations and travel paths
    for office_name, travel in best_solution.attendee_details.items():
        # If the office is the meeting location, we already included its info in the meeting popup
        if office_name == meeting_location.name:
            continue
        office_location = office_locations.get(office_name)
        if not office_location:
            continue
        
        # Office marker
        folium.Marker(
            [office_location.lat, office_location.lon],
            popup=f"<b>{office_name}</b><br>"
                  f"Travel Hours: {travel.total_hours:.2f}<br>"
                  f"CO2: {travel.total_co2:.2f} kg",
            tooltip=office_name,
            icon=folium.Icon(color='blue', icon='building', prefix='fa')
        ).add_to(m)
        
        # Travel path (simplified as straight line)
        folium.PolyLine(
            [[office_location.lat, office_location.lon],
             [meeting_location.lat, meeting_location.lon]],
            popup=f"{office_name} → {meeting_location.name}",
            tooltip=f"{travel.total_hours:.2f} hours, {travel.total_co2:.2f} kg CO2",
            color='red',
            weight=3,
            opacity=0.7
        ).add_to(m)
    
    # Add alternative locations as smaller markers
    for i, solution in enumerate(solutions[1:6], 1):  # Show top 5 alternatives
        alt_location = candidate_cities.get(solution.location)
        if alt_location and alt_location.name != best_solution.location:
            folium.CircleMarker(
                [alt_location.lat, alt_location.lon],
                radius=8,
                popup=f"<b>Alternative {i}: {alt_location.name}</b><br>"
                      f"CO2: {solution.total_co2:.2f} kg<br>"
                      f"Avg Travel: {solution.average_travel_hours:.2f} hours",
                tooltip=f"Alt {i}: {alt_location.name}",
                color='orange',
                fill=True,
                fillColor='orange'
            ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 120px; 
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; border-radius: 5px; padding: 10px">
    <h4>Legend</h4>
    <p><i class="fa fa-star" style="color:green"></i> Meeting Location</p>
    <p><i class="fa fa-building" style="color:blue"></i> Office</p>
    <p><span style="color:orange">●</span> Alternative Locations</p>
    <p style="color:red">━━━</span> Travel Path</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    return str(output_path)


def create_comparison_chart_data(solutions: List[Solution]) -> Dict:
    """Prepare data for comparison charts."""
    if not solutions:
        return {}
    
    cities = [s.location for s in solutions]
    co2_values = [s.total_co2 for s in solutions]
    avg_travel = [s.average_travel_hours for s in solutions]
    fairness_scores = [s.fairness_score for s in solutions]
    max_travel = [s.max_travel_hours for s in solutions]
    
    return {
        "cities": cities,
        "co2_emissions": co2_values,
        "average_travel_hours": avg_travel,
        "max_travel_hours": max_travel,
        "fairness_scores": fairness_scores
    }


def generate_flow_diagram_data(solution: Solution) -> Dict:
    """Generate data for flow diagram visualization."""
    flows = []
    
    for office_name, travel in solution.attendee_details.items():
        if travel.outbound:
            flows.append({
                "from": office_name,
                "to": solution.location,
                "travel_hours": travel.total_hours / 2,  # One way
                "co2": travel.total_co2 / 2,
                "departure": travel.outbound.departure_time.isoformat() if travel.outbound else None,
                "arrival": travel.outbound.arrival_time.isoformat() if travel.outbound else None
            })
    
    return {
        "meeting_location": solution.location,
        "flows": flows,
        "summary": {
            "total_co2": solution.total_co2,
            "average_travel_hours": solution.average_travel_hours,
            "fairness_score": solution.fairness_score
        }
    }

