import pandas as pd

# Load dataset
df = pd.read_csv("C:/Users/banan/Downloads/hackathon 2/Meet-In-Middle/datasets/airports.csv")

# Remove rows where 'iata_code' is missing or empty
df_clean = df[df['iata_code'].notna() & (df['iata_code'] != '')]

# Save filtered version
df_clean.to_csv("C:/Users/banan/Downloads/hackathon 2/Meet-In-Middle/datasets/airports_with_iata.csv", index=False)

