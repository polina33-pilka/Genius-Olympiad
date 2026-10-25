import json
import os
import re
import time

import numpy as np
import pandas as pd
import requests

ELEV_URL = "https://api.open-meteo.com/v1/elevation"
OUT_PATH = "data/processed/elevation_01deg.csv"

LAT_MIN, LAT_MAX = 44.0, 52.6
LON_MIN, LON_MAX = 22.0, 40.5

BATCH = 100
DELAY = 1.0
MAX_RETRIES = 6

# лише комірки, які реально потрапили в наші таблиці
ONLY_NEEDED = True
SOURCES = [
    "data/processed/ambrosia_with_grid.csv",
    "data/processed/climate_data.csv",
    "data/processed/background_climate_data.csv",
    "data/processed/full_grid_climate_data.csv",
]


def fetch_elevations(lats, lons, label):
    params = {"latitude": ",".join(map(str, lats)), "longitude": ",".join(map(str, lons))}

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(ELEV_URL, params=params, timeout=60)
        except requests.exceptions.RequestException as e:
            print(f"Пачка {label}: помилка мережі ({e}), пауза 20 с")
            time.sleep(20)
            continue

        if resp.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"Пачка {label}: ліміт запитів, пауза {wait} с")
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            print(f"Пачка {label}: відповідь {resp.status_code}, пауза 20 с")
            time.sleep(20)
            continue

        try:
            # API іноді повертає голе nan, яке не є коректним JSON
            text = re.sub(r"\bnan\b", "null", resp.text, flags=re.IGNORECASE)
            return json.loads(text)["elevation"]
        except (ValueError, KeyError):
            print(f"Пачка {label}: пошкоджена відповідь, пауза 20 с")
            time.sleep(20)

    return None


lat10 = np.arange(round(LAT_MIN * 10), round(LAT_MAX * 10) + 1)
lon10 = np.arange(round(LON_MIN * 10), round(LON_MAX * 10) + 1)
grid = pd.MultiIndex.from_product([lat10, lon10], names=["lat10", "lon10"]).to_frame(index=False)
print(f"Комірок у сітці: {len(grid)}")

if ONLY_NEEDED:
    needed = set()
    for path in SOURCES:
        if os.path.exists(path):
            cells = pd.read_csv(path, usecols=["lat_grid", "lon_grid"])
            needed |= set(zip((cells["lat_grid"] * 10).round().astype(int),
                              (cells["lon_grid"] * 10).round().astype(int)))
    grid = grid[[k in needed for k in zip(grid["lat10"], grid["lon10"])]].reset_index(drop=True)
    print(f"Потрібних комірок: {len(grid)}")

if os.path.exists(OUT_PATH) and os.path.getsize(OUT_PATH) > 0:
    done = pd.read_csv(OUT_PATH)
    print(f"Вже оброблено: {len(done)}")
else:
    done = pd.DataFrame(columns=["lat10", "lon10", "elevation"])

done_keys = set(zip(done["lat10"], done["lon10"]))
todo = grid[[k not in done_keys for k in zip(grid["lat10"], grid["lon10"])]].reset_index(drop=True)
print(f"Лишилось: {len(todo)}")

results = [done] if len(done) else []

for start in range(0, len(todo), BATCH):
    chunk = todo.iloc[start:start + BATCH]
    lats = (chunk["lat10"] / 10).round(1)
    lons = (chunk["lon10"] / 10).round(1)

    values = fetch_elevations(lats, lons, start)
    if values is None or len(values) != len(chunk):
        print(f"Пачка {start}: дані не отримано. Повторний запуск продовжить з цього місця.")
        break

    part = chunk[["lat10", "lon10"]].copy()
    part["elevation"] = pd.to_numeric(pd.Series(values, index=part.index), errors="coerce")
    results.append(part)

    pd.concat(results, ignore_index=True).to_csv(OUT_PATH, index=False)
    print(f"Збережено {start + len(chunk)} / {len(todo)}")
    time.sleep(DELAY)

if not results:
    raise SystemExit("Жодної комірки не оброблено.")

final = pd.concat(results, ignore_index=True)
final["elevation"] = pd.to_numeric(final["elevation"], errors="coerce")
final["lat_grid"] = (final["lat10"] / 10).round(1)
final["lon_grid"] = (final["lon10"] / 10).round(1)
final.to_csv(OUT_PATH, index=False)

covered = set(zip(final["lat10"], final["lon10"])) & set(zip(grid["lat10"], grid["lon10"]))
print(f"\nКомірок у файлі: {len(final)}")
print(f"Потрібних комірок без висоти: {len(grid) - len(covered)}")
print(f"Без даних про висоту (море тощо): {int(final['elevation'].isna().sum())}")
print(final["elevation"].describe().round(1))
