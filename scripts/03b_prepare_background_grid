import numpy as np
import pandas as pd

from common import SEED, convex_hull, point_in_polygon, scale_polygon

HULL_SCALE = 1.08
N_CANDIDATES = 20000
TARGET_N = 1200

AMBROSIA_PATH = "data/processed/ambrosia_with_grid.csv"
PRESENCE_GRID_PATH = "data/processed/climate_grid_points.csv"
OUT_PATH = "data/processed/background_grid_points.csv"

rng = np.random.RandomState(SEED)

ambrosia = pd.read_csv(AMBROSIA_PATH)
presence_grid = pd.read_csv(PRESENCE_GRID_PATH)
points = ambrosia[["decimalLongitude", "decimalLatitude"]].drop_duplicates().values

hull = np.array(convex_hull(points))
print(f"Вершин опуклої оболонки: {len(hull)}")
hull = scale_polygon(hull, HULL_SCALE)

lon_min, lat_min = hull.min(axis=0)
lon_max, lat_max = hull.max(axis=0)

rand_lons = rng.uniform(lon_min, lon_max, N_CANDIDATES)
rand_lats = rng.uniform(lat_min, lat_max, N_CANDIDATES)

inside = np.array([point_in_polygon(lo, la, hull) for lo, la in zip(rand_lons, rand_lats)])
print(f"Кандидатів: {N_CANDIDATES}, всередині області: {inside.sum()}")

background = pd.DataFrame({
    "lon_grid": rand_lons[inside].round(1),
    "lat_grid": rand_lats[inside].round(1),
}).drop_duplicates()

presence_pairs = set(zip(presence_grid["lat_grid"].round(1), presence_grid["lon_grid"].round(1)))
no_ambrosia = [pair not in presence_pairs for pair in zip(background["lat_grid"], background["lon_grid"])]
background = background[no_ambrosia]
print(f"Унікальних фонових комірок без перетину з presence: {len(background)}")

if len(background) > TARGET_N:
    background = background.sample(n=TARGET_N, random_state=SEED)

background = background[["lat_grid", "lon_grid"]].reset_index(drop=True)
background.to_csv(OUT_PATH, index=False)
print(f"\nЗбережено: {OUT_PATH} ({len(background)} рядків)")
