from climate_fetch import fetch_grid_climate

fetch_grid_climate(
    grid_path="data/processed/full_grid_points.csv",
    output_path="data/processed/full_grid_climate_data.csv",
    base_delay=15.0,
    max_delay=90.0,
)
