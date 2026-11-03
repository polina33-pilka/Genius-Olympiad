import numpy as np
import pandas as pd

from common import convex_hull, point_in_polygon, scale_polygon

LAT_MIN, LAT_MAX = 44.3, 52.4
LON_MIN, LON_MAX = 22.0, 40.3
STEP = 0.25
HULL_SCALE = 1.15

AMBROSIA_PATH = "data/processed/ambrosia_with_grid.csv"
GRID_PATH = "data/processed/full_grid_points.csv"

lats = np.round(np.arange(LAT_MIN, LAT_MAX + STEP, STEP), 1)
lons = np.round(np.arange(LON_MIN, LON_MAX + STEP, STEP), 1)
grid = pd.MultiIndex.from_product([lats, lons], names=["lat_grid", "lon_grid"]).to_frame(index=False)
print(f"Точок у прямокутній сітці: {len(grid)}")

ambrosia = pd.read_csv(AMBROSIA_PATH)
points = ambrosia[["decimalLongitude", "decimalLatitude"]].drop_duplicates().values
hull = scale_polygon(np.array(convex_hull(points)), HULL_SCALE)

in_area = [point_in_polygon(lon, lat, hull) for lat, lon in zip(grid["lat_grid"], grid["lon_grid"])]
grid = grid[in_area].reset_index(drop=True)
print(f"Точок усередині області спостережень: {len(grid)}")

grid.to_csv(GRID_PATH, index=False)
print(f"Збережено: {GRID_PATH}")
