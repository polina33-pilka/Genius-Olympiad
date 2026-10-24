import json
import os
import time
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

START_DATE = "2015-01-01"
END_DATE = "2024-12-31"
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
GEMINI_TIMEOUT = 12
GEMINI_ATTEMPTS = 2

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")

app = Flask(__name__)
CORS(app, origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else "*")

model = joblib.load(os.path.join(DATA_DIR, "ambrosia_risk_model_v2.joblib"))

with open(os.path.join(DATA_DIR, "model_v2_meta.json"), "r", encoding="utf-8") as f:
    META = json.load(f)
FEATURES = META["features"]
T_MEDIUM = META["threshold_medium"]
T_HIGH = META["threshold_high"]

with open(os.path.join(DATA_DIR, "risk_map_v2.geojson"), "r", encoding="utf-8") as f:
    RISK_MAP = json.load(f)
MAP_RISKS = np.sort(np.array([ft["properties"]["risk_percent"] for ft in RISK_MAP["features"]]))

_land = pd.read_csv(os.path.join(DATA_DIR, "landcover_lookup.csv"))
LAND = {
    (int(r.lat10), int(r.lon10)): (float(r.cropland), float(r.built))
    for r in _land.itertuples()
}


def categorize(p):
    if p < T_MEDIUM:
        return "low"
    if p < T_HIGH:
        return "medium"
    return "high"


def percentile_on_map(risk_percent):
    p = np.searchsorted(MAP_RISKS, risk_percent, side="left") / len(MAP_RISKS) * 100
    return int(min(99, max(1, round(p))))


@lru_cache(maxsize=2048)
def fetch_climate(lat_rounded, lon_rounded):
    params = {
        "latitude": lat_rounded,
        "longitude": lon_rounded,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": "temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean",
        "timezone": "auto",
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    daily = pd.DataFrame(data["daily"])
    daily["time"] = pd.to_datetime(daily["time"])
    daily["month"] = daily["time"].dt.month
    season = daily[(daily["month"] >= 5) & (daily["month"] <= 9)]

    climate = {
        "temp_mean": float(season["temperature_2m_mean"].mean()),
        "precip_sum": float(season["precipitation_sum"].mean()),
        "humidity_mean": float(season["relative_humidity_2m_mean"].mean()),
    }
    if any(np.isnan(v) for v in climate.values()):
        raise ValueError("немає кліматичних даних для цієї точки")
    return climate


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/risk-map", methods=["GET"])
def risk_map():
    return jsonify(RISK_MAP)


@app.route("/api/predict", methods=["POST"])
def predict():
    body = request.get_json(force=True, silent=True) or {}
    try:
        lat = float(body["lat"])
        lon = float(body["lon"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Потрібні числові поля 'lat' та 'lon'."}), 400

    lat10 = int(round(lat * 10))
    lon10 = int(round(lon * 10))

    land = LAND.get((lat10, lon10))
    if land is None:
        return jsonify({
            "error": "Для цієї точки немає даних про землекористування "
                     "(море або місце поза територією, яку покриває модель)."
        }), 422

    try:
        climate = fetch_climate(round(lat10 / 10, 1), round(lon10 / 10, 1))
    except Exception as e:
        return jsonify({"error": f"Не вдалось отримати кліматичні дані: {e}"}), 502

    row = {**climate, "cropland": land[0], "built": land[1]}
    X = pd.DataFrame([row], columns=FEATURES)
    risk = float(model.predict_proba(X)[0, 1])
    risk_percent = round(risk * 100, 1)

    return jsonify({
        "lat": lat,
        "lon": lon,
        "risk_percent": risk_percent,
        "risk_category": categorize(risk),
        "percentile": percentile_on_map(risk_percent),
        "climate": climate,
        "land": {"cropland": round(land[0], 3), "built": round(land[1], 3)},
    })


def num(value, digits=1):
    try:
        v = round(float(value), digits)
        return int(v) if digits == 0 else v
    except (TypeError, ValueError):
        return "невідомо"


def pct(value):
    try:
        return int(round(float(value) * 100))
    except (TypeError, ValueError):
        return "невідомо"


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fallback_explanation(lang, place_name, risk_percent, percentile, category, climate, land):
    uk = lang != "en"
    rp = to_float(risk_percent)
    pc = to_float(percentile)
    if rp is None or pc is None:
        return ("Пояснення від ШІ зараз недоступне. Індекс придатності — відносна оцінка того, "
                "наскільки умови схожі на місця, де фіксували амброзію; це не підтверджена "
                "наявність рослини." if uk else
                "The AI explanation is unavailable right now. The suitability index is a relative "
                "estimate of how similar conditions are to places where ragweed has been recorded; "
                "it does not confirm that the plant is present.")
    pc = int(round(pc))
    built = to_float((land or {}).get("built"))
    cropland = to_float((land or {}).get("cropland"))
    temp = to_float((climate or {}).get("temp_mean"))
    hum = to_float((climate or {}).get("humidity_mean"))

    if uk:
        level = {"low": "нижча", "medium": "середня", "high": "вища"}.get(category, "невизначена")
        intro = f"Для місця «{place_name}» " if place_name else "Для цієї точки "
        parts = [intro + f"індекс придатності становить {rp:.1f}% (категорія: {level}), "
                          f"тобто більше, ніж на {pc}% території України."]

        drivers = []
        if built is not None and built >= 0.15:
            drivers.append("значна частка забудови")
        if cropland is not None and cropland >= 0.4:
            drivers.append("значна частка пашні")
        if drivers:
            parts.append("В околі є " + " і ".join(drivers) +
                         ", а такі порушені землі амброзія заселяє найлегше.")
        else:
            parts.append("Частка пашні та забудови в околі невелика.")
        if temp is not None and hum is not None:
            parts.append(f"Середня температура за сезон травень-вересень — {temp:.1f} °C, "
                         f"вологість — {hum:.0f}%.")
        parts.append("Це орієнтовна оцінка схожості умов на місця, де фіксували амброзію, "
                     "а не підтверджена наявність рослини.")
        if category == "low":
            parts.append("Поодинокі рослини можливі й тут: помічену амброзію варто "
                         "видаляти з корінням до цвітіння.")
        else:
            parts.append("Алергікам у період цвітіння (серпень-вересень) варто обмежувати "
                         "перебування на вулиці в сухі вітряні дні, а помічену рослину "
                         "видаляти з корінням до утворення насіння.")
        return " ".join(parts)

    level = {"low": "lower", "medium": "medium", "high": "higher"}.get(category, "undetermined")
    intro = f"For {place_name}, " if place_name else "For this point, "
    parts = [intro + f"the suitability index is {rp:.1f}% (category: {level}), "
                      f"which is higher than in {pc}% of Ukraine's territory."]
    drivers = []
    if built is not None and built >= 0.15:
        drivers.append("a large share of built-up land")
    if cropland is not None and cropland >= 0.4:
        drivers.append("a large share of cropland")
    if drivers:
        parts.append("The surroundings have " + " and ".join(drivers) +
                     ", the kind of disturbed land ragweed colonises most easily.")
    else:
        parts.append("The share of cropland and built-up land nearby is small.")
    if temp is not None and hum is not None:
        parts.append(f"The mean May-September temperature is {temp:.1f} °C and humidity is {hum:.0f}%.")
    parts.append("This is a rough estimate of how similar conditions are to places where "
                 "ragweed has been recorded, not confirmation that the plant is present.")
    if category == "low":
        parts.append("Single plants are still possible here: pull any ragweed you notice, "
                     "roots included, before it flows.")
    else:
        parts.append("People with allergies should limit time outdoors on dry, windy days "
                     "during flowering (August-September), and any ragweed you find should "
                     "be pulled out with its roots before it sets seed.")
    return " ".join(parts)


@app.route("/api/explain", methods=["POST"])
def explain():
    body = request.get_json(force=True, silent=True) or {}

    lang = body.get("lang", "uk")
    lat = num(body.get("lat"), 3)
    lon = num(body.get("lon"), 3)
    risk_percent = num(body.get("risk_percent"))
    percentile = num(body.get("percentile"), 0)
    category = body.get("risk_category")
    climate = body.get("climate") or {}
    land = body.get("land") or {}

    place_name = " ".join(str(body.get("placeName") or "").split())[:120]
    place_part = f", місце: {place_name}" if place_name else ""
    cat_label = {"low": "низька", "medium": "середня", "high": "висока"}.get(category, "невідома")

    crop_pct = pct(land.get("cropland"))
    built_pct = pct(land.get("built"))

    lang_instruction = "Відповідай українською мовою." if lang == "uk" else "Respond in English."

    prompt = (
        f"{lang_instruction}\n\n"
        "Ти - асистент екологічного сайту про інвазивну рослину амброзію полинолисту "
        "(Ambrosia artemisiifolia) в Україні.\n"
        "Модель машинного навчання оцінила, наскільки умови в цій місцевості схожі на ті, "
        f"де амброзію вже фіксували (координати {lat}, {lon}{place_part}). "
        "Це відносний індекс придатності, а не ймовірність того, що амброзія тут росте.\n"
        f"- Індекс: {risk_percent}% (вище, ніж на {percentile}% території України; "
        f"категорія: {cat_label})\n"
        f"- Середня температура за сезон (травень-вересень): {num(climate.get('temp_mean'))} C\n"
        f"- Середні опади за сезон: {num(climate.get('precip_sum'))} мм/день\n"
        f"- Середня вологість: {num(climate.get('humidity_mean'))}%\n"
        f"- Частка пашні в околі: {crop_pct}%\n"
        f"- Частка забудови в околі: {built_pct}%\n\n"
        "Напиши коротке (3-5 речень) пояснення для звичайної людини: що означає такий "
        "результат, які з цих умов могли на нього вплинути і яку практичну пораду можна "
        "дати (алергія, контроль бур'яну). Наприкінці одним реченням зазнач, що це "
        "орієнтовна оцінка, а не підтверджена наявність рослини.\n\n"
        "Ніколи не називай індекс ймовірністю чи шансом появи амброзії, це лише відносна оцінка схожості умов. "
        "Тон обережний: модель має помірну точність, тому не вживай слів на кшталт "
        "«надзвичайно», «ідеальні», «гарантовано». "
        "Починай одразу з суті, без вступних фраз на кшталт «Ось пояснення». "
        "Не використовуй заголовків, списків і форматування, лише звичайний текст."
    )

    last_error = None if GEMINI_API_KEY else "GEMINI_API_KEY не налаштовано"
    text = None
    for attempt in range(GEMINI_ATTEMPTS if GEMINI_API_KEY else 0):
        try:
            resp = requests.post(
                GEMINI_URL,
                headers={
                    "x-goog-api-key": GEMINI_API_KEY,
                    "Content-Type": "application/json",
                },
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=GEMINI_TIMEOUT,
            )
            if resp.status_code == 503:
                last_error = "503: " + resp.text[:300]
                time.sleep(2 * (attempt + 1))
                continue
            if resp.status_code != 200:
                last_error = f"{resp.status_code}: {resp.text[:300]}"
                break
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            break
        except Exception as e:
            last_error = str(e)
            time.sleep(2 * (attempt + 1))

    if text is None:
        return jsonify({
            "explanation": fallback_explanation(
                lang, place_name, risk_percent, percentile, category, climate, land),
            "fallback": True,
        })

    return jsonify({"explanation": text})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
