import pandas as pd

RANDOM_SEED = 42

AMBROSIA_PATH = "data/processed/ambrosia_with_grid.csv"
PRESENCE_CLIMATE_PATH = "data/processed/climate_data.csv"
BACKGROUND_CLIMATE_PATH = "data/processed/background_climate_data.csv"
TRAINING_PATH = "data/processed/training_data.csv"

CLIMATE_COLUMNS = ["temp_mean", "precip_sum", "humidity_mean"]

ambrosia = pd.read_csv(AMBROSIA_PATH)
climate = pd.read_csv(PRESENCE_CLIMATE_PATH)
background_climate = pd.read_csv(BACKGROUND_CLIMATE_PATH)

print(f"Записів амброзії: {len(ambrosia)}")
print(f"Кліматичних точок (presence): {len(climate)}, (фон): {len(background_climate)}")

presence_cells = ambrosia[["lat_grid", "lon_grid"]].drop_duplicates().copy()
presence_cells["presence"] = 1
print(f"Унікальних presence-комірок: {len(presence_cells)}")

presence_full = presence_cells.merge(climate, on=["lat_grid", "lon_grid"], how="inner")
print(f"З кліматом: {len(presence_full)}")

missing = len(presence_cells) - len(presence_full)
if missing > 0:
    print(f"УВАГА: {missing} presence-комірок без кліматичних даних, їх пропущено.")

n_absence = min(len(presence_full), len(background_climate))
pseudo_absence = background_climate.sample(n=n_absence, random_state=RANDOM_SEED).copy()
pseudo_absence["presence"] = 0
print(f"Обрано pseudo-absence комірок: {len(pseudo_absence)}")

training_data = pd.concat([presence_full, pseudo_absence], ignore_index=True)
training_data = training_data.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

empty = int(training_data[CLIMATE_COLUMNS].isna().any(axis=1).sum())
if empty:
    print(f"УВАГА: у {empty} рядках немає кліматичних значень (NaN).")

print(f"\nДатасет: {len(training_data)} рядків "
      f"(presence {(training_data['presence'] == 1).sum()}, "
      f"pseudo-absence {(training_data['presence'] == 0).sum()})")
print("Колонки:", training_data.columns.tolist())
print(training_data.head())

training_data.to_csv(TRAINING_PATH, index=False)
print(f"\nЗбережено: {TRAINING_PATH}")
