from pathlib import Path

import pandas as pd

from common import MAX_UNCERTAINTY_M, YEAR_FROM, YEAR_TO

RAW_PATH = Path("data/raw/ambrosia_ukraine_gbif.csv")
CLEAN_PATH = Path("data/processed/ambrosia_clean.csv")

KEEP_COLUMNS = ["gbifID", "decimalLatitude", "decimalLongitude", "year", "month", "day", "stateProvince"]


def keep(df, mask, label):
    df = df[mask]
    print(f"{label}: {len(df)}")
    return df


df = pd.read_csv(RAW_PATH, sep="\t", low_memory=False)
print(f"Завантажено записів: {len(df)}")

df = keep(df, df[["year", "month", "day"]].notna().all(axis=1), "повна дата")
df = keep(df, df[["decimalLatitude", "decimalLongitude"]].notna().all(axis=1), "є координати")
df = keep(df, df["basisOfRecord"] == "HUMAN_OBSERVATION", "лише спостереження людей")
df = keep(df, df["year"].between(YEAR_FROM, YEAR_TO), f"роки {YEAR_FROM}-{YEAR_TO}")

uncertainty = df["coordinateUncertaintyInMeters"]
df = keep(df, uncertainty.isna() | (uncertainty <= MAX_UNCERTAINTY_M), f"точність до {MAX_UNCERTAINTY_M} м")

same_place_and_day = pd.DataFrame({
    "lat": df["decimalLatitude"].round(4),
    "lon": df["decimalLongitude"].round(4),
    "year": df["year"],
    "month": df["month"],
    "day": df["day"],
})
df = keep(df, ~same_place_and_day.duplicated(), "без дублікатів (те саме місце й день)")

CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
df[KEEP_COLUMNS].to_csv(CLEAN_PATH, index=False)
print(f"\nЗбережено {len(df)} записів у {CLEAN_PATH}")
