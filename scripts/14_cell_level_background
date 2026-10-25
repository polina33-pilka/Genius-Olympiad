import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.model_selection import GroupKFold, StratifiedKFold, cross_val_score

from common import CLIMATE, LAND, SEED, load_plants, make_rf, spatial_blocks, to_km

PLANTS_PATH = "data/raw/plants_ukraine_gbif.csv"
OUT_PATH = "data/processed/training_data_cell.csv"
SEEDS = [SEED, SEED + 1, SEED + 2]
MAX_CLIMATE_DIST_KM = 25.0

ambrosia = pd.read_csv("data/processed/ambrosia_with_grid.csv")
presence = ambrosia[["lat_grid", "lon_grid"]].drop_duplicates().copy()
presence["lat10"] = np.rint(presence["lat_grid"] * 10).astype(int)
presence["lon10"] = np.rint(presence["lon_grid"] * 10).astype(int)
presence = presence[["lat10", "lon10"]].drop_duplicates()
presence_keys = set(zip(presence["lat10"], presence["lon10"]))
print(f"Presence-комірок: {len(presence)}")

# візити: записи рослин на комірку 0.1°
plants = load_plants(PLANTS_PATH)
plants["lat10"] = np.rint(plants["decimalLatitude"] * 10).astype(int)
plants["lon10"] = np.rint(plants["decimalLongitude"] * 10).astype(int)
visits = plants.groupby(["lat10", "lon10"]).size().rename("visits").reset_index()
print(f"Комірок зі спостереженнями рослин: {len(visits)}")

land = pd.read_csv("data/processed/landcover_01deg.csv")[["lat10", "lon10"] + LAND]

reference = pd.concat([
    pd.read_csv("data/processed/background_climate_data.csv"),
    pd.read_csv("data/processed/full_grid_climate_data.csv"),
], ignore_index=True)
reference = reference.dropna(subset=CLIMATE).drop_duplicates(["lat_grid", "lon_grid"])
climate_tree = cKDTree(to_km(reference["lat_grid"].values, reference["lon_grid"].values))


def add_features(cells):
    cells = cells.merge(land, on=["lat10", "lon10"], how="left")
    dist, idx = climate_tree.query(to_km(cells["lat10"] / 10, cells["lon10"] / 10))
    climate = reference.iloc[idx][CLIMATE].reset_index(drop=True)
    cells = pd.concat([cells.reset_index(drop=True), climate], axis=1)
    cells["clim_dist_km"] = dist
    cells = cells[cells["clim_dist_km"] <= MAX_CLIMATE_DIST_KM]
    return cells.dropna(subset=LAND + ["temp_mean"]).drop(columns="clim_dist_km")


presence = add_features(presence.copy())
presence["presence"] = 1
presence = presence.merge(visits, on=["lat10", "lon10"], how="left").fillna({"visits": 0})

not_ambrosia = [k not in presence_keys for k in zip(visits["lat10"], visits["lon10"])]
candidates = add_features(visits[not_ambrosia].copy())
print(f"Presence з ознаками: {len(presence)}, кандидатів на фон: {len(candidates)}")

feature_sets = {
    "клімат": CLIMATE,
    "лише земля": LAND,
    "клімат + земля": CLIMATE + LAND,
    "лише lat/lon (діагностика)": ["lat_grid", "lon_grid"],
}

rows = []
for seed in SEEDS:
    rng = np.random.default_rng(seed)
    p = candidates["visits"].values / candidates["visits"].values.sum()
    chosen = rng.choice(len(candidates), size=min(len(presence), len(candidates)), replace=False, p=p)
    background = candidates.iloc[chosen].copy()
    background["presence"] = 0

    data = pd.concat([presence, background], ignore_index=True)
    data["lat_grid"] = data["lat10"] / 10
    data["lon_grid"] = data["lon10"] / 10

    if seed == SEEDS[0]:
        data.to_csv(OUT_PATH, index=False)
        print(f"\nPresence і фон (seed {seed}), середні значення:")
        print(data.groupby("presence")[["visits", "cropland", "built", "temp_mean"]].mean().round(3))

    y = data["presence"]
    blocks = spatial_blocks(data)
    random_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    for name, cols in feature_sets.items():
        forest = make_rf(seed)
        random_auc = cross_val_score(forest, data[cols], y, cv=random_cv, scoring="roc_auc").mean()
        spatial_auc = cross_val_score(forest, data[cols], y, cv=GroupKFold(n_splits=5),
                                      groups=blocks, scoring="roc_auc").mean()
        rows.append({"ознаки": name, "seed": seed, "random": random_auc, "regions": spatial_auc})

summary = pd.DataFrame(rows).groupby("ознаки", sort=False)[["random", "regions"]].agg(["mean", "std"]).round(3)
print(f"\nRandom Forest, фон на рівні комірки (середнє по {len(SEEDS)} вибірках):")
print(summary.to_string())
