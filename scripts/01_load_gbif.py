import pandas as pd

RAW_PATH = "data/raw/ambrosia_ukraine_gbif.csv"
KEY_COLUMNS = ["gbifID", "decimalLatitude", "decimalLongitude", "eventDate", "year", "month", "day"]

df = pd.read_csv(RAW_PATH, sep="\t", low_memory=False)

print(f"Рядків: {len(df)}, стовпців: {df.shape[1]}")
print("\nСтовпці:")
print(df.columns.tolist())
print()
print(df[KEY_COLUMNS].head())

has_full_date = df[["year", "month", "day"]].notna().all(axis=1)
print(f"\nЗ повною датою: {has_full_date.sum()}")
print(f"Без повної дати: {(~has_full_date).sum()}")
