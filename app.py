"""
Main web application for meeting location optimizer.
"""
from pathlib import Path

from flask import Flask, render_template, request, jsonify, url_for
import json
from algorithm import MeetingOptimizer, Solution
from data_handler import load_office_locations, load_travel_data, parse_input_json, create_comparison_output, find_city_location

# Optional visualization imports
try:
    from visualization import create_map_visualization, create_comparison_chart_data, generate_flow_diagram_data
    VISUALIZATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Visualization module not available: {e}")
    VISUALIZATION_AVAILABLE = False
    # Create stub functions
    def create_map_visualization(*args, **kwargs):
        return None
    def create_comparison_chart_data(*args, **kwargs):
        return {}
    def generate_flow_diagram_data(*args, **kwargs):
        return {}

app = Flask(__name__)

# Initialize optimizer
office_locations = load_office_locations()
travel_data = load_travel_data("datasets/emissions.csv")
# Note: we create a request-scoped MeetingOptimizer in the handler so we can
# enrich office locations dynamically from worldcities.csv when the JSON
# input contains offices not present in the fixed office list.


@app.route('/')
def index():
    """Main page with interactive interface."""
    return render_template('index.html')


@app.route('/api/optimize', methods=['POST'])
def optimize():
    """
    API endpoint for optimizing meeting location.
    Accepts JSON input and returns optimized solution.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Parse and validate input
        input_data = parse_input_json(data)
        
<<<<<<< HEAD
=======
        # Use fixed equal weighting between emissions and fairness
        co2_weight = 0.5
        fairness_weight = 0.5

>>>>>>> 939be9141584d116ead8a58d1e7fef6304f34fc5
        # Build an office_locations mapping for this request and enrich it using
        # worldcities.csv for any attendee city names not in the defaults.
        local_offices = load_office_locations()
        for office_name in input_data['attendees'].keys():
            if office_name not in local_offices:
                try:
                    loc = find_city_location(office_name)
                    local_offices[office_name] = loc
                except Exception as e:
                    return jsonify({'error': f"Unknown office '{office_name}' and not found in worldcities: {str(e)}"}), 400

        # Create a request-scoped optimizer with the enriched office list
        optimizer = MeetingOptimizer(travel_data, local_offices)

        # Optimize
        solutions = optimizer.optimize_location(
            attendees=input_data['attendees'],
            availability_window=input_data['availability_window'],
            event_duration=input_data['event_duration'],
            top_n=10
        )
        
        if not solutions:
            return jsonify({'error': 'No solutions found'}), 404
        
        # Convert solutions to dictionaries
        solution_dicts = [optimizer.solution_to_dict(sol) for sol in solutions]
        
        # Get visualization data
        best_solution = solutions[0]
        chart_data = {}
        flow_data = {}
        map_path = None
        
        if VISUALIZATION_AVAILABLE:
            try:
                chart_data = create_comparison_chart_data(solutions)
                flow_data = generate_flow_diagram_data(best_solution)
                
                # Create map visualization
                map_file = Path(app.static_folder) / 'map_visualization.html'
                map_path = create_map_visualization(
                    solutions,
                    local_offices,
                    optimizer.candidate_cities,
                    output_path=map_file
                )
            except Exception as e:
                print(f"Warning: Visualization generation failed: {e}")
        
        # Create comparison output
        comparison = create_comparison_output(solution_dicts)
        
        response = {
            'solution': solution_dicts[0],
            'alternatives': solution_dicts[1:],
            'comparison': comparison,
            'visualization': {
                'chart_data': chart_data,
                'flow_data': flow_data,
                'map_path': url_for('static', filename='map_visualization.html') if map_path else None
            }
        }
        
        return jsonify(response)
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Internal error: {str(e)}'}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})

@app.route('/api/debug_csv', methods=['GET'])
def debug_csv():
    """Return sample CO2 data from emissions.csv for verification."""
    # Pick a sample flight from your loaded data
    sample_origin = "CGK"
    sample_dest = "SUB"

    flights = travel_data.get("flights", {})
    if sample_origin in flights and sample_dest in flights[sample_origin]:
        return jsonify(flights[sample_origin][sample_dest])
    else:
        return jsonify({"error": "Sample flight not found"})


if __name__ == '__main__':
    app.run(debug=True, port=5000)

