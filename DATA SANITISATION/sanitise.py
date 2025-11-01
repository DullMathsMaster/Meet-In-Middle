import pandas as pd

# === 1. Load the data ===
# Replace 'flights.csv' with your actual filename
df = pd.read_csv('C:/Users/banan/Downloads/hackathon 2/Meet-In-Middle/emissions.csv')

# === 2. Create a directionless route key ===
# This ensures that DEPARTURE→ARRIVAL and ARRIVAL→DEPARTURE are treated as the same route
df['ROUTE'] = df.apply(
    lambda x: '-'.join(sorted([x['DEPARTURE_AIRPORT'], x['ARRIVAL_AIRPORT']])),
    axis=1
)

# === 3. Group by route and calculate statistics ===
route_stats = (
    df.groupby('ROUTE', as_index=False)
      .agg(
          AVERAGE_CO2_TONNES=('ESTIMATED_CO2_TOTAL_TONNES', 'mean'),
          FLIGHT_COUNT=('ESTIMATED_CO2_TOTAL_TONNES', 'count')
      )
)

# === 4. Sort by average CO₂ descending (optional) ===
route_stats = route_stats.sort_values('AVERAGE_CO2_TONNES', ascending=False)

# === 5. Save results ===
route_stats.to_csv('average_co2_by_route.csv', index=False)

# === 6. Display summary ===
print(route_stats.head(20))  # show top 20 routes by average CO₂
