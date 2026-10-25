import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from common import CLIMATE, SEED, load_plants, to_km

RADIUS_KM = 15.0
PLANTS_PATH = "data/raw/plants_ukraine_gbif.csv"
OUT_PATH = "data/processed/training_data_tg.csv"

rng = np.random.default_rng(SEED)

ambrosia = pd.read_csv("data/processed/ambrosia_with_grid.csv")
climate = pd.read_csv("data/processed/climate_data.csv")

presence_cells = ambrosia[["lat_grid", "lon_grid"]].drop_duplicates().copy()
presence_cells["presence"] = 1
presence = presence_cells.merge(climate, on=["lat_grid", "lon_grid"], how="inner")
print(f"Presence-комірок з кліматом: {len(presence)}")

plants = load_plants(PLANTS_PATH)
print(f"Записів рослин після фільтрів: {len(plants)}")

candidates = pd.concat([
    pd.read_csv("data/processed/background_climate_data.csv"),
    pd.read_csv("data/processed/full_grid_climate_data.csv"),
], ignore_index=True)
candidates["lat_grid"] = candidates["lat_grid"].round(1)
candidates["lon_grid"] = candidates["lon_grid"].round(1)
candidates = candidates.drop_duplicates(subset=["lat_grid", "lon_grid"])

presence_pairs = set(zip(presence["lat_grid"].round(1), presence["lon_grid"].round(1)))
no_ambrosia = [pair not in presence_pairs for pair in zip(candidates["lat_grid"], candidates["lon_grid"])]
candidates = candidates[no_ambrosia].copy()
print(f"Кандидатів без комірок з амброзією: {len(candidates)}")

# вага комірки: скільки записів рослин у радіусі RADIUS_KM
tree = cKDTree(to_km(plants["decimalLatitude"].values, plants["decimalLongitude"].values))
candidates["weight"] = tree.query_ball_point(
    to_km(candidates["lat_grid"].values, candidates["lon_grid"].values),
    r=RADIUS_KM, return_length=True,
)
usable = candidates[candidates["weight"] > 0].copy()
print(f"З ненульовою вагою: {len(usable)}")

n_absence = min(len(presence), len(usable))
if n_absence < len(presence):
    print(f"Для pseudo-absence доступно лише {n_absence} точок")

p = usable["weight"].values / usable["weight"].values.sum()
chosen = rng.choice(len(usable), size=n_absence, replace=False, p=p)
background = usable.iloc[chosen][["lat_grid", "lon_grid"] + CLIMATE].copy()
background["presence"] = 0

training = pd.concat([presence, background], ignore_index=True)
training = training.sample(frac=1, random_state=SEED).reset_index(drop=True)

print(f"\nДатасет: {len(training)} рядків "
      f"(presence {int((training['presence'] == 1).sum())}, "
      f"фон {int((training['presence'] == 0).sum())})")
print("Середній клімат:")
print(training.groupby("presence")[CLIMATE].mean().round(2))

training.to_csv(OUT_PATH, index=False)
print(f"\nЗбережено: {OUT_PATH}")
