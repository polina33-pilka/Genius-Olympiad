from climate_fetch import fetch_grid_climate

fetch_grid_climate(
    grid_path="data/processed/climate_grid_points.csv",
    output_path="data/processed/climate_data.csv",
    base_delay=10.0,
    max_delay=60.0,
)
