import os
import time

import pandas as pd
import requests

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
START_DATE = "2015-01-01"
END_DATE = "2024-12-31"
DAILY_VARIABLES = "temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean"
SEASON_FIRST_MONTH, SEASON_LAST_MONTH = 5, 9

BATCH_SIZE = 50
MAX_RETRIES = 5
PAUSE_ON_ERROR = 30

COLUMNS = ["lat_grid", "lon_grid", "temp_mean", "precip_sum", "humidity_mean"]


def round_pair(lat, lon):
    return round(lat, 1), round(lon, 1)


def load_done_pairs(output_path):
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        print("Файлу прогресу ще немає, починаємо з нуля.")
        return set()
    try:
        done = pd.read_csv(output_path)
    except pd.errors.EmptyDataError:
        print("Файл прогресу порожній, починаємо з нуля.")
        open(output_path, "w").close()
        return set()
    pairs = set(zip(done["lat_grid"].round(1), done["lon_grid"].round(1)))
    print(f"Вже оброблено точок: {len(pairs)}, продовжуємо.")
    return pairs


def append_rows(output_path, rows):
    needs_header = not os.path.exists(output_path) or os.path.getsize(output_path) == 0
    pd.DataFrame(rows, columns=COLUMNS).to_csv(
        output_path, mode="a", header=needs_header, index=False
    )


def fetch_batch(label, lats, lons, delay, max_delay):
    params = {
        "latitude": ",".join(map(str, lats)),
        "longitude": ",".join(map(str, lons)),
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": DAILY_VARIABLES,
        "timezone": "auto",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(BASE_URL, params=params, timeout=90)
        except requests.exceptions.RequestException as e:
            print(f"Пачка {label}: помилка мережі ({e}), пауза {PAUSE_ON_ERROR} с")
            time.sleep(PAUSE_ON_ERROR)
            continue

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            wait = int(retry_after) if retry_after else 60 * attempt
            print(f"Пачка {label}: ліміт запитів ({attempt}/{MAX_RETRIES}), пауза {wait} с")
            time.sleep(wait)
            delay = min(delay * 1.5, max_delay)
            continue

        if response.status_code != 200:
            print(f"Пачка {label}: відповідь {response.status_code}, пауза {PAUSE_ON_ERROR} с")
            time.sleep(PAUSE_ON_ERROR)
            continue

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"Пачка {label}: пошкоджена відповідь ({attempt}/{MAX_RETRIES}), пауза {PAUSE_ON_ERROR} с")
            time.sleep(PAUSE_ON_ERROR)
            continue

        # для однієї точки API повертає об'єкт, а не список
        return (data if isinstance(data, list) else [data]), delay

    return None, delay


def season_means(location_data):
    daily = pd.DataFrame(location_data["daily"])
    month = pd.to_datetime(daily["time"]).dt.month
    season = daily[(month >= SEASON_FIRST_MONTH) & (month <= SEASON_LAST_MONTH)]
    return {
        "temp_mean": season["temperature_2m_mean"].mean(),
        "precip_sum": season["precipitation_sum"].mean(),
        "humidity_mean": season["relative_humidity_2m_mean"].mean(),
    }


def report_coverage(grid, output_path):
    needed = set(zip(grid["lat_grid"].round(1), grid["lon_grid"].round(1)))
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        print(f"Потрібно {len(needed)}, не вистачає {len(needed)}")
        return
    done = pd.read_csv(output_path)
    have = set(zip(done["lat_grid"].round(1), done["lon_grid"].round(1)))
    print(f"Потрібно {len(needed)}, не вистачає {len(needed - have)}")
    empty = int(done[["temp_mean", "precip_sum", "humidity_mean"]].isna().any(axis=1).sum())
    if empty:
        print(f"УВАГА: у {empty} точок немає кліматичних значень (NaN).")


def fetch_grid_climate(grid_path, output_path, base_delay, max_delay):
    grid = pd.read_csv(grid_path)
    print(f"Комірок для обробки: {len(grid)}")

    lats = grid["lat_grid"].tolist()
    lons = grid["lon_grid"].tolist()
    done_pairs = load_done_pairs(output_path)
    delay = base_delay

    for start in range(0, len(lats), BATCH_SIZE):
        pending = [
            (la, lo)
            for la, lo in zip(lats[start:start + BATCH_SIZE], lons[start:start + BATCH_SIZE])
            if round_pair(la, lo) not in done_pairs
        ]
        if not pending:
            print(f"Пачка {start}: уже оброблена, пропускаємо.")
            continue

        batch_lats = [p[0] for p in pending]
        batch_lons = [p[1] for p in pending]

        data, delay = fetch_batch(start, batch_lats, batch_lons, delay, max_delay)
        if data is None:
            print(f"Пачка {start}: не вдалося отримати дані після {MAX_RETRIES} спроб. "
                  "Зупиняємось, повторний запуск продовжить з цього місця.")
            break
        if len(data) != len(pending):
            print(f"Пачка {start}: очікували {len(pending)} точок, отримали {len(data)}. Зупиняємось.")
            break

        rows = [
            {"lat_grid": la, "lon_grid": lo, **season_means(location)}
            for la, lo, location in zip(batch_lats, batch_lons, data)
        ]
        append_rows(output_path, rows)
        done_pairs.update(round_pair(la, lo) for la, lo in zip(batch_lats, batch_lons))

        print(f"Збережено {len(done_pairs)} / {len(lats)} (пауза {delay:.0f} с)")
        time.sleep(delay)
        delay = max(base_delay, delay * 0.9)

    print("\nГотово або зупинено для повторного запуску.")
    report_coverage(grid, output_path)
