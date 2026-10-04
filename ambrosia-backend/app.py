import os
import json
from functools import lru_cache

import joblib
import numpy as np
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "data", "ambrosia_risk_model.joblib")
RISK_MAP_PATH = os.path.join(BASE_DIR, "data", "risk_map.geojson")

START_DATE = "2015-01-01"
END_DATE = "2024-12-31"
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*") 

app = Flask(__name__)
CORS(app, origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else "*")

model = joblib.load(MODEL_PATH)

with open(RISK_MAP_PATH, "r", encoding="utf-8") as f:
    RISK_MAP = json.load(f)


def categorize(p):
    if p < 0.33:
        return "low"
    elif p < 0.66:
        return "medium"
    return "high"


@lru_cache(maxsize=2048)
def fetch_climate(lat_rounded, lon_rounded):
    """Качає кліматичні дані для координат (округлених до 0.1) з кешем,
    щоб не бити по Open-Meteo повторно за ту саму точку."""
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

    import pandas as pd

    daily = pd.DataFrame(data["daily"])
    daily["time"] = pd.to_datetime(daily["time"])
    daily["month"] = daily["time"].dt.month
    season = daily[(daily["month"] >= 5) & (daily["month"] <= 9)]

    return {
        "temp_mean": float(season["temperature_2m_mean"].mean()),
        "precip_sum": float(season["precipitation_sum"].mean()),
        "humidity_mean": float(season["relative_humidity_2m_mean"].mean()),
    }


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/risk-map", methods=["GET"])
def risk_map():
    """Віддає готову GeoJSON-карту ризику (1852 точки) для відображення."""
    return jsonify(RISK_MAP)


@app.route("/api/predict", methods=["POST"])
def predict():
    body = request.get_json(force=True, silent=True) or {}
    try:
        lat = float(body["lat"])
        lon = float(body["lon"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Потрібні числові поля 'lat' та 'lon'."}), 400

    lat_rounded = round(lat, 1)
    lon_rounded = round(lon, 1)

    try:
        climate = fetch_climate(lat_rounded, lon_rounded)
    except Exception as e:
        return jsonify({"error": f"Не вдалось отримати кліматичні дані: {e}"}), 502

    X = np.array([[climate["temp_mean"], climate["precip_sum"], climate["humidity_mean"]]])
    risk_proba = float(model.predict_proba(X)[0, 1])

    return jsonify({
        "lat": lat,
        "lon": lon,
        "risk_percent": round(risk_proba * 100, 1),
        "risk_category": categorize(risk_proba),
        "climate": climate,
    })


@app.route("/api/explain", methods=["POST"])
def explain():
    body = request.get_json(force=True, silent=True) or {}

    if not GEMINI_API_KEY:
        return jsonify({"error": "GEMINI_API_KEY не налаштовано на сервері."}), 500

    lang = body.get("lang", "uk")
    lat = body.get("lat")
    lon = body.get("lon")
    risk_percent = body.get("risk_percent")
    risk_category = body.get("risk_category")
    climate = body.get("climate", {})

    lang_instruction = "Відповідай українською мовою." if lang == "uk" else "Respond in English."

    prompt = (
        f"{lang_instruction}\n\n"
        f"Ти - асистент екологічного сайту про інвазивний вид рослини "
        f"амброзія полинолиста (Ambrosia artemisiifolia) в Україні.\n"
        f"Модель машинного навчання оцінила ризик присутності амброзії "
        f"для координат ({lat}, {lon}):\n"
        f"- Ризик: {risk_percent}% (категорія: {risk_category})\n"
        f"- Середня температура за сезон (травень-вересень): {climate.get('temp_mean')} C\n"
        f"- Середні опади за сезон: {climate.get('precip_sum')} мм/день\n"
        f"- Середня вологість: {climate.get('humidity_mean')}%\n\n"
        f"Напиши коротке (3-5 речень), зрозуміле пояснення цього результату "
        f"для звичайної людини: що означає такий рівень ризику, чому саме "
        f"такі кліматичні умови впливають на поширення амброзії, і яку "
        f"практичну пораду можна дати (наприклад, про алергію, контроль бур'яну)."
    )

    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return jsonify({"error": f"Помилка звернення до Gemini: {e}"}), 502

    return jsonify({"explanation": text})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
