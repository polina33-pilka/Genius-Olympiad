import json

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import GroupKFold, cross_val_score

from common import CLIMATE, LAND, make_rf, spatial_blocks

FEATURES = CLIMATE + LAND
Q_MEDIUM, Q_HIGH = 0.50, 0.80

OUT_DIR = "data/processed/"

d = pd.read_csv(OUT_DIR + "training_data_cell.csv")
X, y = d[FEATURES], d["presence"]
blocks = spatial_blocks(d)

cv_auc = cross_val_score(make_rf(n_estimators=500), X, y, cv=GroupKFold(n_splits=5),
                         groups=blocks, scoring="roc_auc")
print(f"AUC по регіонах (5 фолдів): {cv_auc.mean():.3f} +/- {cv_auc.std():.3f}")

model = make_rf(n_estimators=500).fit(X, y)
joblib.dump(model, OUT_DIR + "ambrosia_risk_model_v2.joblib")
importance = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
print("\nВажливість ознак:")
print(importance.round(3).to_string())

grid = pd.read_csv(OUT_DIR + "full_grid_climate_data.csv")
grid["lat10"] = np.rint(grid["lat_grid"] * 10).astype(int)
grid["lon10"] = np.rint(grid["lon_grid"] * 10).astype(int)
land = pd.read_csv(OUT_DIR + "landcover_01deg.csv")[["lat10", "lon10"] + LAND]
grid = grid.merge(land, on=["lat10", "lon10"], how="left")
n_before = len(grid)
grid = grid.dropna(subset=FEATURES).reset_index(drop=True)
print(f"\nТочок карти: {n_before} -> {len(grid)} (без даних про землю: море, поза покриттям)")

grid["risk"] = model.predict_proba(grid[FEATURES])[:, 1]
t_medium = float(grid["risk"].quantile(Q_MEDIUM))
t_high = float(grid["risk"].quantile(Q_HIGH))


def category(p):
    if p < t_medium:
        return "low"
    return "medium" if p < t_high else "high"


grid["risk_percent"] = (grid["risk"] * 100).round(1)
grid["risk_category"] = grid["risk"].apply(category)
print("Категорії на карті:")
print(grid["risk_category"].value_counts().to_string())

features = [
    {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(r.lon_grid), float(r.lat_grid)]},
        "properties": {"risk_percent": float(r.risk_percent), "risk_category": r.risk_category},
    }
    for r in grid.itertuples()
]
with open(OUT_DIR + "risk_map_v2.geojson", "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False)

# довідник землі для бекенду: за ним сайт знаходить частки для будь-якої точки
land.dropna().round({"cropland": 3, "built": 3}).to_csv(OUT_DIR + "landcover_lookup.csv", index=False)

meta = {
    "features": FEATURES,
    "threshold_medium": t_medium,
    "threshold_high": t_high,
    "cv_auc_regions": round(float(cv_auc.mean()), 3),
    "sklearn_version": sklearn.__version__,
}
with open(OUT_DIR + "model_v2_meta.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print(f"\nЗбережено в {OUT_DIR}: ambrosia_risk_model_v2.joblib, risk_map_v2.geojson, "
      "landcover_lookup.csv, model_v2_meta.json")
print("Версія scikit-learn:", sklearn.__version__)
