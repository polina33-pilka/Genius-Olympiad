import os
import sys
import warnings

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

FILES = {
    "cropland": "data/raw/WorldCover_cropland_30s.tif",
    "built": "data/raw/WorldCover_built_30s.tif",
}
OUT_PATH = "data/processed/landcover_01deg.csv"

LAT_MIN10, LAT_MAX10 = 440, 526
LON_MIN10, LON_MAX10 = 220, 405
N_LAT = LAT_MAX10 - LAT_MIN10 + 1
N_LON = LON_MAX10 - LON_MIN10 + 1

BLOCK = 12  # 0.1° це 12 пікселів по 30 кутових секунд


def aggregate(path, name):
    with rasterio.open(path) as src:
        t = src.transform
        px, py = t.a, -t.e
        if abs(px - 1 / 120) > 1e-6 or abs(py - 1 / 120) > 1e-6:
            sys.exit(f"{name}: розмір пікселя {px} x {py}, очікувався 1/120 градуса. "
                     "Перевірте, що це файл *_30s.tif.")

        left = LON_MIN10 / 10 - 0.05
        top = LAT_MAX10 / 10 + 0.05
        col_f = (left - t.c) / px
        row_f = (t.f - top) / py
        col_off, row_off = round(col_f), round(row_f)
        if abs(col_f - col_off) > 0.01 or abs(row_f - row_off) > 0.01:
            print(f"{name}: межі пікселів не збігаються з сіткою, похибка до півпікселя.")

        width, height = N_LON * BLOCK, N_LAT * BLOCK
        if col_off < 0 or row_off < 0 or col_off + width > src.width or row_off + height > src.height:
            sys.exit(f"{name}: потрібна ділянка виходить за межі растра. "
                     "Перевірте, що файл покриває Україну.")

        arr = src.read(1, window=Window(col_off, row_off, width, height), masked=True)

    data = np.ma.filled(arr.astype("float32"), np.nan)
    data[data < 0] = np.nan

    top_val = np.nanmax(data) if np.isfinite(data).any() else 0
    if top_val > 1.5:
        print(f"{name}: значення схожі на відсотки (макс {top_val:.0f}), ділю на 100.")
        data = data / 100.0
    else:
        print(f"{name}: значення вже частки 0-1 (макс {top_val:.2f}).")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        blocks = data.reshape(N_LAT, BLOCK, N_LON, BLOCK)
        return np.nanmean(blocks, axis=(1, 3))


lat10 = LAT_MAX10 - np.arange(N_LAT)
lon10 = LON_MIN10 + np.arange(N_LON)
lat_g, lon_g = np.meshgrid(lat10, lon10, indexing="ij")

table = pd.DataFrame({"lat10": lat_g.ravel(), "lon10": lon_g.ravel()})
for name, path in FILES.items():
    if not os.path.exists(path):
        sys.exit(f"Не знайдено файл {path}. Покладіть його в data/raw/.")
    print(f"Обробляю {path}")
    table[name] = aggregate(path, name).ravel()

table["lat_grid"] = (table["lat10"] / 10).round(1)
table["lon_grid"] = (table["lon10"] / 10).round(1)
table = table.sort_values(["lat10", "lon10"]).reset_index(drop=True)
table.to_csv(OUT_PATH, index=False)

print(f"\nЗбережено: {OUT_PATH} ({len(table)} комірок)")
print(table[["cropland", "built"]].describe().round(3))

# контрольні місця: значення мають бути правдоподібними
checks = [
    ("Київ", 50.4, 30.5),
    ("Полтавщина", 49.6, 34.5),
    ("Карпати", 48.4, 24.5),
    ("Одеса", 46.5, 30.7),
    ("Херсонщина", 46.6, 32.6),
]
print("\nКонтрольні точки:")
for label, lat, lon in checks:
    row = table[(table["lat10"] == round(lat * 10)) & (table["lon10"] == round(lon * 10))]
    if len(row):
        r = row.iloc[0]
        print(f"  {label:12s} рілля {r['cropland']:.2f}  забудова {r['built']:.2f}")
