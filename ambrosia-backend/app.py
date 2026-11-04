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
GEMINI_TIMEOUT = 20
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

GRID_CLIMATE = pd.read_csv(os.path.join(DATA_DIR, "full_grid_climate_data_v3.csv")).dropna()
GRID_LAT = GRID_CLIMATE["lat_grid"].to_numpy()
GRID_LON = GRID_CLIMATE["lon_grid"].to_numpy()

# Фіксовані поради: однакові для всіх, не залежать від ШІ
TIP_GROUPS = {
    "uk": [
        {"title": "Комунальним службам та ОТГ", "items": [
            "Оглянути узбіччя, пустирі та будмайданчики до початку цвітіння й заплановати скошування.",
        ]},
        {"title": "Аграріям та землевласникам", "items": [
            "Перевірити краї полів і перелоги та не допустити утворення насіння.",
        ]},
        {"title": "Мешканцям", "items": [
            "Тримати в порядку власну ділянку й повідомляти владі про великі зарості поруч із домом.",
        ]},
        {"title": "Алергікам", "items": [
            "У серпні-вересні стежити за місцевими прогнозами пилку й планувати час надворі.",
        ]},
    ],
    "en": [
        {"title": "Municipal services and local communities", "items": [
            "Inspect roadsides, vacant lots and construction sites before flowering and plan mowing.",
        ]},
        {"title": "Farmers and landowners", "items": [
            "Check field margins and fallow land and prevent seed formation.",
        ]},
        {"title": "Residents", "items": [
            "Keep your own plot tidy and report large patches of weeds near your home to the authorities.",
        ]},
        {"title": "People with allergies", "items": [
            "In August-September follow local pollen forecasts and plan time outdoors.",
        ]},
    ],
}

CLOSING = {
    "uk": "Цей показник оцінює сприятливість клімату й землі, а не гарантує факт наявності рослини на ділянці прямо зараз.",
    "en": "This index reflects how suitable the climate and land are, not a guarantee that the plant is present on the site right now.",
}

def nearest_grid_climate(lat, lon, max_deg=0.3):
    d = np.hypot(GRID_LAT - lat, (GRID_LON - lon) * np.cos(np.radians(lat)))
    i = int(d.argmin())
    if d[i] > max_deg:
        return None
    row = GRID_CLIMATE.iloc[i]
    return {
        "temp_mean": float(row["temp_mean"]),
        "precip_sum": float(row["precip_sum"]),
        "humidity_mean": float(row["humidity_mean"]),
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
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
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
        return jsonify({
            "error": "Потрібні числові поля 'lat' та 'lon'.",
            "code": "invalid_coords",
        }), 400

    lat10 = int(round(lat * 10))
    lon10 = int(round(lon * 10))

    land = LAND.get((lat10, lon10))
    if land is None:
        return jsonify({
            "error": "Для цієї точки немає даних про землекористування "
                     "(море або місце поза територією, яку покриває модель).",
            "code": "no_land_data",
        }), 422

    source = "live"
    try:
        climate = fetch_climate(round(lat10 / 10, 1), round(lon10 / 10, 1))
    except Exception as e:
        print(f"climate fallback: {e}")
        climate = nearest_grid_climate(lat, lon)
        source = "grid"
        if climate is None:
            return jsonify({
                "error": f"Не вдалось отримати кліматичні дані: {e}",
                "code": "climate_failed",
            }), 502

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
        "climate_source": source,
        "land": {"cropland": round(land[0], 3), "built": round(land[1], 3)},
    })


def dec(value, lang):
    text = str(value)
    return text if lang == "en" else text.replace(".", ",")


def num(value, digits=1, unknown="невідомо"):
    try:
        v = round(float(value), digits)
        return int(v) if digits == 0 else v
    except (TypeError, ValueError):
        return unknown


def pct(value, unknown="невідомо"):
    try:
        return int(round(float(value) * 100))
    except (TypeError, ValueError):
        return unknown


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
        return ("Пояснення від ШІ зараз не вдалося отримати. Індекс придатності є відносною "
                "оцінкою того, наскільки умови схожі на місця, де фіксували амброзію." if uk else
                "The AI explanation could not be obtained right now. The suitability index is a "
                "relative estimate of how similar conditions are to places where ragweed has been "
                "recorded.")
    pc = int(round(pc))
    built = to_float((land or {}).get("built"))
    cropland = to_float((land or {}).get("cropland"))

    if uk:
        level = {"low": "нижча", "medium": "середня", "high": "вища"}.get(category, "невизначена")
        intro = f"Для місця «{place_name}» " if place_name else "Для цієї точки "
        parts = [intro + f"індекс придатності становить {dec(f'{rp:.1f}', 'uk')}% (категорія: {level}), "
                          f"тобто вище, ніж на {pc}% території України."]
        drivers = []
        if built is not None and built >= 0.15:
            drivers.append("значна частка забудови")
        if cropland is not None and cropland >= 0.4:
            drivers.append("значна частка ріллі")
        if drivers:
            parts.append("На результат могла вплинути " + " і ".join(drivers) + " в околі.")
        else:
            parts.append("Частка ріллі та забудови в околі невелика.")
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
        parts.append("The result may be influenced by " + " and ".join(drivers) + " nearby.")
    else:
        parts.append("The share of cropland and built-up land nearby is small.")
    return " ".join(parts)


LEVEL_LABEL = {
    "uk": {"low": "нижча", "medium": "середня", "high": "вища"},
    "en": {"low": "lower", "medium": "medium", "high": "higher"},
}


def build_prompt(lang, lat, lon, place_name, risk_percent, percentile, category, climate, land):
    titles = [g["title"] for g in TIP_GROUPS[lang]]
    if lang == "en":
        place_part = place_name or "this point"
        level_rule = {
            "low": "Index is lower: the tips are PREVENTIVE (routine observation, keeping things "
                   "tidy, awareness), not urgent.",
            "medium": "Index is medium: targeted checks of typical places and planning before flowering.",
            "high": "Index is higher: prioritised actions (inspections and mowing before flowering, "
                    "preventing seed formation), businesslike and without alarm.",
        }.get(category, "Keep a cautious tone.")
        return (
            "Respond in English only.\n\n"
            "You are an ecological consultant. Explain a machine learning model result about "
            "common ragweed (Ambrosia artemisiifolia) in Ukraine in natural, restrained, clear "
            "language for an adult.\n\n"
            f"INPUT:\n- Place: {place_part}\n"
            f"- Suitability index: {risk_percent}% (category: {LEVEL_LABEL['en'].get(category, 'unknown')})\n"
            f"- Share of cropland: {pct(land.get('cropland'), 'unknown')}%\n"
            f"- Share of built-up land: {pct(land.get('built'), 'unknown')}%\n"
            f"- Mean May-September temperature: {num(climate.get('temp_mean'), 1, 'unknown')} °C\n"
            f"- Mean precipitation: {num(climate.get('precip_sum'), 1, 'unknown')} mm/day\n\n"
            "Return ONLY a JSON object, no markdown:\n"
            '{"reason": "...", "actions": ["...", "...", "...", "..."]}\n\n'
            "RULES:\n"
            "- reason: ONE sentence naming which factor (cropland, built-up share, temperature or "
            "precipitation) most likely influenced this index. Do not claim the conditions "
            "definitely promote or hold back the plant. No introductory phrases, no childish "
            "wording, no heavy bureaucratic words, no comparison with other regions.\n"
            "- actions: you MUST ALWAYS generate all four, at EVERY index level including lower, "
            "never skip or leave one empty. One short concrete sentence each (up to 20 words), for: "
            f"1) {titles[0]}; 2) {titles[1]}; 3) {titles[2]}; 4) {titles[3]}.\n"
            f"- {level_rule} At a lower level change only the character of the tips to preventive, "
            "do not drop any of the four.\n"
            "- The four groups must be different and must not repeat each other. Residents (3) "
            "are about their own plots and reporting overgrown land. People with allergies (4) "
            "are about the flowering season (August-September) and planning time outdoors, "
            "following pollen forecasts, scaled to the index level.\n"
            "- Adapt to the data: high cropland share, more specific action for landowners "
            "(field margins, fallow land); high built-up share, more specific action for "
            "municipal services (vacant lots, roadsides, construction sites).\n"
            "- No household tips (washing hair, closing windows), no doctors, no medications.\n"
            "- Never call the index a probability. No herbicides or doses. No long dashes. "
            "Do not add a disclaimer, it is added separately.\n"
            "- Style: concise, businesslike, grounded in the landscape."
        )

    place_part = place_name or "ця точка"
    level_rule = {
        "low": "Індекс нижчий: поради ПРОФІЛАКТИЧНІ (періодичне спостереження, підтримання порядку, "
               "обізнаність), не термінові.",
        "medium": "Індекс середній: цілеспрямовані огляди типових місць і планування перед цвітінням.",
        "high": "Індекс вищий: пріоритетні дії (огляди й скошування до цвітіння, недопущення "
                "утворення насіння), по-діловому й без тривоги.",
    }.get(category, "Тон обережний.")
    return (
        "Відповідай лише українською мовою.\n\n"
        "Ти екологічний консультант. Твоє завдання: пояснити результат моделі машинного навчання "
        "про амброзію полинолисту (Ambrosia artemisiifolia) в Україні природною, стриманою та "
        "зрозумілою мовою для дорослого користувача.\n\n"
        f"ВХІДНІ ДАНІ:\n- Місце: {place_part}\n"
        f"- Індекс придатності: {dec(risk_percent, 'uk')}% (категорія: {LEVEL_LABEL['uk'].get(category, 'невідома')})\n"
        f"- Частка ріллі: {pct(land.get('cropland'))}%\n"
        f"- Частка забудови: {pct(land.get('built'))}%\n"
        f"- Середня температура травня-вересня: {dec(num(climate.get('temp_mean')), 'uk')} °C\n"
        f"- Середні опади: {dec(num(climate.get('precip_sum')), 'uk')} мм/день\n\n"
        "Поверни ЛИШЕ JSON-об'єкт, без markdown:\n"
        '{"reason": "...", "actions": ["...", "...", "...", "..."]}\n\n'
        "ПРАВИЛА:\n"
        "- reason: ОДНЕ речення про те, який фактор (рілля, забудова, температура чи опади) "
        "найімовірніше вплинув на цей індекс. Не стверджуй, що умови точно сприяють рослині чи "
        "стримують її. Без вступних фраз («Простими словами:»), без дитячих зворотів, без важкої "
        "канцелярії («експансія», «вегетаційний період»), без порівнянь з іншими регіонами.\n"
        "- actions: ти ЗОБОВ'ЯЗАНИЙ ЗАВЖДИ згенерувати всі чотири пункти, за БУДЬ-ЯКОГО рівня "
        "індексу, зокрема нижчого, і ніколи не пропускати та не залишати порожніх. По одному "
        f"короткому конкретному реченню (до 20 слів), для: 1) {titles[0]}; 2) {titles[1]}; "
        f"3) {titles[2]}; 4) {titles[3]}.\n"
        f"- {level_rule} За нижчого рівня змінюється лише характер порад на профілактичний, "
        "жоден із чотирьох пунктів не випадає.\n"
        "- Чотири групи мають різнитися й не повторювати одна одну. Мешканці (3): власна ділянка "
        "та повідомлення про занедбані зарості. Алергіки (4): сезон цвітіння (серпень-вересень), "
        "планування часу надворі та стеження за прогнозами пилку, відповідно до рівня індексу.\n"
        "- Підлаштуй під дані: висока частка ріллі, конкретніша дія для землевласників (краї "
        "полів, перелоги); висока частка забудови, конкретніша дія для комунальних служб "
        "(пустирі, узбіччя, будмайданчики).\n"
        "- БЕЗ побутових порад (миття волосся, зачинені вікна), БЕЗ згадок про лікарів і ліки.\n"
        "- Ніколи не називай індекс ймовірністю. Без гербіцидів і доз. Без довгих тире. "
        "Пиши грамотно, вживай «рілля». Десяткові числа через кому. "
        "Не додавай застереження, воно додається окремо.\n"
        "- Стиль: лаконічний, діловий, ландшафтно-обґрунтований, без дитячого тону й без "
        "академічного занудства."
    )


def parse_llm_json(text, lang):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:]
    data = json.loads(text)
    reason = str(data["reason"]).strip()
    actions = [str(a).strip() for a in data["actions"]]
    if not reason or len(actions) != 4 or not all(actions):
        raise ValueError("unexpected structure")
    titles = [g["title"] for g in TIP_GROUPS[lang]]
    groups = [{"title": t, "items": [a]} for t, a in zip(titles, actions)]
    return reason, groups

@app.route("/api/explain", methods=["POST"])
def explain():
    body = request.get_json(force=True, silent=True) or {}

    lang = "en" if body.get("lang") == "en" else "uk"
    unknown = "unknown" if lang == "en" else "невідомо"
    lat = num(body.get("lat"), 3, unknown)
    lon = num(body.get("lon"), 3, unknown)
    risk_percent = num(body.get("risk_percent"), 1, unknown)
    percentile = num(body.get("percentile"), 0, unknown)
    category = body.get("risk_category")
    climate = body.get("climate") or {}
    land = body.get("land") or {}

    place_name = " ".join(str(body.get("placeName") or "").split())[:120]

    prompt = build_prompt(lang, lat, lon, place_name, risk_percent, percentile,
                          category, climate, land)
    closing = CLOSING[lang]

    label = LEVEL_LABEL[lang].get(category, "")
    if lang == "en":
        intro = f"The suitability index is {risk_percent}% ({label} category)."
    else:
        intro = f"Індекс придатності становить {dec(risk_percent, 'uk')}% ({label} категорія)."

    reason = None
    groups = []
    last_error = None if GEMINI_API_KEY else "GEMINI_API_KEY не налаштовано"
    for attempt in range(GEMINI_ATTEMPTS if GEMINI_API_KEY else 0):
        try:
            resp = requests.post(
                GEMINI_URL,
                headers={
                    "x-goog-api-key": GEMINI_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"},
                },
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
            reason, groups = parse_llm_json(text, lang)
            break
        except Exception as e:
            last_error = str(e)
            reason = None
            time.sleep(2 * (attempt + 1))

    if reason is None:
        print(f"explain fallback: {last_error}")
        return jsonify({
            "explanation": fallback_explanation(
                lang, place_name, risk_percent, percentile, category, climate, land),
            "groups": TIP_GROUPS[lang],
            "closing": closing,
            "fallback": True,
        })

    return jsonify({"explanation": f"{intro} {reason}", "groups": groups, "closing": closing})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
