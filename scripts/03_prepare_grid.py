from pathlib import Path

import pandas as pd

CLEAN_PATH = Path("data/processed/ambrosia_clean.csv")
GRID_POINTS_PATH = Path("data/processed/climate_grid_points.csv")
WITH_GRID_PATH = Path("data/processed/ambrosia_with_grid.csv")

df = pd.read_csv(CLEAN_PATH)

df["lat_grid"] = df["decimalLatitude"].round(1)
df["lon_grid"] = df["decimalLongitude"].round(1)

cells = df[["lat_grid", "lon_grid"]].drop_duplicates()
print(f"Записів: {len(df)}, унікальних комірок 0.1°: {len(cells)}")
print(f"Запитів до Open-Meteo: {len(cells)} замість {len(df)}")

GRID_POINTS_PATH.parent.mkdir(parents=True, exist_ok=True)
cells.to_csv(GRID_POINTS_PATH, index=False)
df.to_csv(WITH_GRID_PATH, index=False)
print(f"Збережено: {GRID_POINTS_PATH}, {WITH_GRID_PATH}")
