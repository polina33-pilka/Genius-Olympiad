import pandas as pd

from ukraine_border import in_ukraine

OUT = "data/processed/"

land = pd.read_csv(OUT + "landcover_01deg.csv").dropna(subset=["cropland", "built"])
land_keys = set(zip(land["lat10"], land["lon10"]))

points = [
    (la / 10, lo / 10)
    for la in range(440, 526, 2)
    for lo in range(220, 406, 2)
    if (la, lo) in land_keys and in_ukraine(lo / 10, la / 10)
]
grid = pd.DataFrame(points, columns=["lat_grid", "lon_grid"]).round(1)
grid.to_csv(OUT + "full_grid_points_v3.csv", index=False)
print(f"Точок нової сітки: {len(grid)}")

old = pd.read_csv(OUT + "full_grid_climate_data.csv").round({"lat_grid": 1, "lon_grid": 1})
reused = old.merge(grid, on=["lat_grid", "lon_grid"])
reused.to_csv(OUT + "full_grid_climate_data_v3.csv", index=False)
print(f"Клімат перенесено зі старого файлу: {len(reused)}, треба докачати: {len(grid) - len(reused)}")
