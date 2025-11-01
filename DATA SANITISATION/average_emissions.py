"""Create average CO2 per-route statistics.

This script computes per-person CO2 (in tonnes) for each flight using an
occupancy multiplier, groups by (directionless) route, then writes a CSV
with both per-person (tonnes and kg) and per-flight average values.

Output columns:
- ROUTE
- AVERAGE_CO2_PER_PERSON_TONNES
- AVERAGE_CO2_PER_PERSON_KG
- AVERAGE_CO2_TONNES  (average per-flight total, tonnes)
- FLIGHT_COUNT

Place this file in DATA SANITISATION; it will write to datasets/average_co2_by_route.csv
relative to the project root.
"""

import pandas as pd
from pathlib import Path

# Paths (project-relative)
BASE = Path(__file__).resolve().parent.parent  # Meet-In-Middle/
INPUT_CSV = BASE / 'datasets' / 'emissions.csv'
OUTPUT_CSV = BASE / 'datasets' / 'average_co2_by_route.csv'

if not INPUT_CSV.exists():
    raise FileNotFoundError(f"Input emissions file not found: {INPUT_CSV}")

# === 1. Load the data ===
df = pd.read_csv(INPUT_CSV)

# === 2. Calculate per-person emissions for each flight ===
# Assuming some average occupancy (85% of seats filled)
PASSENGER_CAPACITY_MULTIPLIER = 0.85
df['PASSENGERS'] = df['SEATS'] * PASSENGER_CAPACITY_MULTIPLIER
# Safely avoid division by zero
df['PASSENGERS'] = df['PASSENGERS'].replace({0: pd.NA})
df['CO2_PER_PERSON_TONNES'] = df['ESTIMATED_CO2_TOTAL_TONNES'] / df['PASSENGERS']

# === 3. Create a directionless route key ===
# This ensures that DEPARTURE→ARRIVAL and ARRIVAL→DEPARTURE are treated as the same route
df['ROUTE'] = df.apply(
    lambda x: '-'.join(sorted([str(x['DEPARTURE_AIRPORT']), str(x['ARRIVAL_AIRPORT'])])),
    axis=1
)

# === 4. Group by route and calculate statistics ===
route_stats = (
    df.groupby('ROUTE', as_index=False)
      .agg(
          AVERAGE_CO2_PER_PERSON_TONNES=('CO2_PER_PERSON_TONNES', 'mean'),
          AVERAGE_CO2_TONNES=('ESTIMATED_CO2_TOTAL_TONNES', 'mean'),
          FLIGHT_COUNT=('ESTIMATED_CO2_TOTAL_TONNES', 'count')
      )
)

# Convert per-person tonnes -> kg for convenience
route_stats['AVERAGE_CO2_PER_PERSON_KG'] = route_stats['AVERAGE_CO2_PER_PERSON_TONNES'] * 1000.0

# Reorder columns for readability
cols = ['ROUTE', 'AVERAGE_CO2_PER_PERSON_TONNES', 'AVERAGE_CO2_PER_PERSON_KG', 'AVERAGE_CO2_TONNES', 'FLIGHT_COUNT']
route_stats = route_stats[cols]

# === 5. Sort and save results ===
route_stats = route_stats.sort_values('AVERAGE_CO2_PER_PERSON_TONNES', ascending=False)
route_stats.to_csv(OUTPUT_CSV, index=False)

print(f"Wrote {len(route_stats)} routes to {OUTPUT_CSV}")
print(route_stats.head(20))
