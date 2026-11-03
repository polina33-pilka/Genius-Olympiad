import csv

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

SEED = 42
YEAR_FROM, YEAR_TO = 2015, 2024
MAX_UNCERTAINTY_M = 5000
BLOCK_SIZE = 2.0
LAT0 = 48.5

CLIMATE = ["temp_mean", "precip_sum", "humidity_mean"]
LAND = ["cropland", "built"]

PLANT_COLUMNS = ["decimalLatitude", "decimalLongitude", "coordinateUncertaintyInMeters",
                 "year", "month", "day"]


def load_plants(path):
    header = pd.read_csv(path, sep="\t", nrows=0, quoting=csv.QUOTE_NONE).columns
    missing = [c for c in PLANT_COLUMNS if c not in header]
    if missing:
        raise SystemExit(f"У файлі рослин немає колонок: {missing}")

    plants = pd.read_csv(path, sep="\t", usecols=PLANT_COLUMNS, quoting=csv.QUOTE_NONE,
                         on_bad_lines="skip", low_memory=False)
    plants = plants.apply(pd.to_numeric, errors="coerce")

    plants = plants.dropna(subset=["decimalLatitude", "decimalLongitude", "year", "month", "day"])
    plants = plants[plants["year"].between(YEAR_FROM, YEAR_TO)]
    uncertainty = plants["coordinateUncertaintyInMeters"]
    plants = plants[uncertainty.isna() | (uncertainty <= MAX_UNCERTAINTY_M)]

    same_visit = pd.DataFrame({
        "lat": plants["decimalLatitude"].round(4),
        "lon": plants["decimalLongitude"].round(4),
        "year": plants["year"],
        "month": plants["month"],
        "day": plants["day"],
    })
    return plants[~same_visit.duplicated()].copy()


def spatial_blocks(df, size=BLOCK_SIZE):
    lat_block = (df["lat_grid"] // size).astype(int).astype(str)
    lon_block = (df["lon_grid"] // size).astype(int).astype(str)
    return lat_block + "_" + lon_block


def make_rf(seed=SEED, n_estimators=300):
    return RandomForestClassifier(n_estimators=n_estimators, max_depth=8, min_samples_leaf=3,
                                  class_weight="balanced", random_state=seed)


def to_km(lat, lon):
    return np.column_stack([
        np.asarray(lon) * 111.32 * np.cos(np.radians(LAT0)),
        np.asarray(lat) * 110.57,
    ])


def convex_hull(points):
    points = sorted(set(map(tuple, points)))
    if len(points) <= 2:
        return points

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def half_hull(seq):
        hull = []
        for p in seq:
            while len(hull) >= 2 and cross(hull[-2], hull[-1], p) <= 0:
                hull.pop()
            hull.append(p)
        return hull

    lower = half_hull(points)
    upper = half_hull(reversed(points))
    return lower[:-1] + upper[:-1]


def scale_polygon(polygon, factor):
    center = polygon.mean(axis=0)
    return center + (polygon - center) * factor


def point_in_polygon(x, y, polygon):
    result = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            result = not result
        j = i
    return result
