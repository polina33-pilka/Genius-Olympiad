import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import GroupKFold, StratifiedKFold, cross_val_score

from common import CLIMATE, SEED, make_rf, spatial_blocks

TRAINING_PATH = "data/processed/training_data_tg.csv"
FEATURES_PATH = "data/processed/training_data_tg_feat.csv"
COMPARISON_PATH = "data/processed/feature_set_comparison.csv"

data = pd.read_csv(TRAINING_PATH)
data["lat10"] = (data["lat_grid"] * 10).round().astype(int)
data["lon10"] = (data["lon_grid"] * 10).round().astype(int)

elevation = pd.read_csv("data/processed/elevation_01deg.csv")[["lat10", "lon10", "elevation"]]
land = pd.read_csv("data/processed/landcover_01deg.csv")[["lat10", "lon10", "cropland", "built"]]

n_before = len(data)
data = data.merge(elevation, on=["lat10", "lon10"], how="left")
data = data.merge(land, on=["lat10", "lon10"], how="left")

for col in ["elevation", "cropland", "built"]:
    print(f"Без значення {col}: {int(data[col].isna().sum())}")
data = data.dropna(subset=["elevation", "cropland", "built"]).reset_index(drop=True)
print(f"Рядків: {n_before} -> {len(data)}\n")

data.to_csv(FEATURES_PATH, index=False)

y = data["presence"]
blocks = spatial_blocks(data)

feature_sets = {
    "клімат": CLIMATE,
    "клімат + висота": CLIMATE + ["elevation"],
    "клімат + земля": CLIMATE + ["cropland", "built"],
    "клімат + висота + земля": CLIMATE + ["elevation", "cropland", "built"],
    "лише земля + висота": ["elevation", "cropland", "built"],
    "лише lat/lon (діагностика)": ["lat_grid", "lon_grid"],
}


def make_models():
    return {
        "Random Forest": make_rf(),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.05, random_state=SEED),
    }


random_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
spatial_cv = GroupKFold(n_splits=5)

rows = []
for set_name, cols in feature_sets.items():
    for model_name, model in make_models().items():
        r = cross_val_score(model, data[cols], y, cv=random_cv, scoring="roc_auc")
        s = cross_val_score(model, data[cols], y, cv=spatial_cv, groups=blocks, scoring="roc_auc")
        rows.append({
            "ознаки": set_name,
            "модель": model_name,
            "AUC випадкова": round(r.mean(), 3),
            "AUC по регіонах": round(s.mean(), 3),
            "std по регіонах": round(s.std(), 3),
        })

results = pd.DataFrame(rows)
print("Порівняння наборів ознак (AUC-ROC, 5 фолдів):")
print(results.to_string(index=False))
results.to_csv(COMPARISON_PATH, index=False)

all_cols = feature_sets["клімат + висота + земля"]
forest = make_rf().fit(data[all_cols], y)
importance = pd.Series(forest.feature_importances_, index=all_cols).sort_values(ascending=False)
print("\nВажливість ознак (Random Forest, усі ознаки):")
print(importance.round(3).to_string())
print(f"\nЗбережено: {FEATURES_PATH}, {COMPARISON_PATH}")
