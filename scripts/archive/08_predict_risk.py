import json

import joblib
import pandas as pd

from common import CLIMATE

# перша версія карти: модель v1 і фіксовані пороги; актуальна карта будується у 16
MODEL_PATH = "data/processed/ambrosia_risk_model.joblib"
CLIMATE_PATH = "data/processed/full_grid_climate_data.csv"
CSV_PATH = "data/processed/risk_map.csv"
GEOJSON_PATH = "data/processed/risk_map.geojson"


def category(p):
    if p < 0.33:
        return "low"
    if p < 0.66:
        return "medium"
    return "high"


model = joblib.load(MODEL_PATH)
grid = pd.read_csv(CLIMATE_PATH)
print(f"Точок для прогнозу: {len(grid)}")

n = len(grid)
grid = grid.dropna(subset=CLIMATE).reset_index(drop=True)
if len(grid) < n:
    print(f"Пропущено {n - len(grid)} рядків без кліматичних даних.")

grid["risk_score"] = model.predict_proba(grid[CLIMATE])[:, 1]
grid["risk_percent"] = (grid["risk_score"] * 100).round(1)
grid["risk_category"] = grid["risk_score"].apply(category)

print("\nРозподіл по категоріях:")
print(grid["risk_category"].value_counts())

result = grid[["lat_grid", "lon_grid", "risk_percent", "risk_category"]]
result.to_csv(CSV_PATH, index=False)

features = [
    {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
        "properties": {"risk_percent": float(percent), "risk_category": cat},
    }
    for lat, lon, percent, cat in result.itertuples(index=False)
]
with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False)
print(f"Збережено: {CSV_PATH}, {GEOJSON_PATH}")
