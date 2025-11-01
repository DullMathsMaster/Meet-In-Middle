"""
Command-line interface for the meeting location optimizer.
"""
import json
import argparse
import sys
from algorithm import MeetingOptimizer
from data_handler import load_office_locations, load_travel_data, load_input_from_file, save_output_json, create_comparison_output
from visualization import create_map_visualization


def main():
    parser = argparse.ArgumentParser(description='Optimize meeting location balancing CO2 and fairness')
    parser.add_argument('input_file', help='Input JSON file with meeting parameters')
    parser.add_argument('-o', '--output', help='Output JSON file path', default='output.json')
    parser.add_argument('--co2-weight', type=float, default=0.5, help='Weight for CO2 emissions (0-1)')
    parser.add_argument('--fairness-weight', type=float, default=0.5, help='Weight for fairness (0-1)')
    parser.add_argument('--top-n', type=int, default=5, help='Number of top solutions to return')
    parser.add_argument('--map', help='Generate map visualization (HTML file path)')
    
    args = parser.parse_args()
    
    try:
        # Load input
        input_data = load_input_from_file(args.input_file)
        
        # Initialize optimizer
        office_locations = load_office_locations()
        travel_data = load_travel_data()
        optimizer = MeetingOptimizer(travel_data, office_locations)
        
        # Normalize weights
        total_weight = args.co2_weight + args.fairness_weight
        if total_weight > 0:
            co2_weight = args.co2_weight / total_weight
            fairness_weight = args.fairness_weight / total_weight
        else:
            co2_weight = 0.5
            fairness_weight = 0.5
        
        # Optimize
        print("Optimizing meeting location...")
        solutions = optimizer.optimize_location(
            attendees=input_data['attendees'],
            availability_window=input_data['availability_window'],
            event_duration=input_data['event_duration'],
            co2_weight=co2_weight,
            fairness_weight=fairness_weight,
            top_n=args.top_n
        )
        
        if not solutions:
            print("Error: No solutions found", file=sys.stderr)
            sys.exit(1)
        
        # Convert to dictionaries
        solution_dicts = [optimizer.solution_to_dict(sol) for sol in solutions]
        
        # Create comparison output
        output_data = create_comparison_output(solution_dicts)
        
        # Save output
        save_output_json(output_data, args.output)
        print(f"Results saved to {args.output}")
        
        # Generate map if requested
        if args.map:
            create_map_visualization(
                solutions,
                office_locations,
                optimizer.candidate_cities,
                output_path=args.map
            )
            print(f"Map visualization saved to {args.map}")
        
        # Print summary
        best = solution_dicts[0]
        print("\n=== Best Solution ===")
        print(f"Location: {best['event_location']}")
        print(f"Total CO2: {best['total_co2']} kg")
        print(f"Average Travel Hours: {best['average_travel_hours']}")
        print(f"Fairness Score: {best.get('fairness_score', 'N/A')}")
        
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

