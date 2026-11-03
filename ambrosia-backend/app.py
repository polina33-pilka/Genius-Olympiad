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
        {
            "title": "Комунальним службам та ОТГ",
            "items": [
                "Перед цвітінням (з липня) оглядати узбіччя, пустирі, будівельні майданчики та занедбані ділянки.",
                "Планувати скошування таких місць до початку цвітіння рослин.",
                "Фіксувати знайдені осередки (місце й дата), щоб планувати повторні огляди.",
            ],
        },
        {
            "title": "Аграріям та фермерам",
            "items": [
                "З червня-липня перевіряти краї полів, перелоги та необроблені ділянки.",
                "Не допускати цвітіння й утворення насіння на таких ділянках.",
                "Щодо методів боротьби радитися з агрономом або місцевою службою захисту рослин.",
            ],
        },
        {
            "title": "Мешканцям та алергікам",
            "items": [
                "Повідомляти місцевій владі про великі зарості на занедбаних ділянках поруч із домом.",
                "У серпні-вересні стежити за місцевими прогнозами пилку.",
                "З питань симптомів і лікування звертатися до лікаря.",
            ],
        },
    ],
    "en": [
        {
            "title": "Municipal services and local communities",
            "items": [
                "Before flowering (from July), inspect roadsides, vacant lots, construction sites and neglected land.",
                "Plan mowing of such places before the plants start flowering.",
                "Record any hotspots found (place and date) to plan repeat inspections.",
            ],
        },
        {
            "title": "Farmers and agricultural producers",
            "items": [
                "From June-July, check field margins, fallow land and uncultivated areas.",
                "Do not let plants flower and set seed on such areas.",
                "Ask an agronomist or the local plant protection service about control methods.",
            ],
        },
        {
            "title": "Residents and people with allergies",
            "items": [
                "Tell local authorities about large patches of weeds on neglected land near homes.",
                "In August-September, follow local pollen forecasts.",
                "For questions about symptoms and treatment, consult a doctor.",
            ],
        },
    ],
}

CLOSING = {
    "uk": "Це орієнтовна оцінка, а не підтверджена наявність рослини, а поради загальні й не замінюють рекомендацій місцевих служб чи лікаря.",
    "en": "This is a rough estimate, not confirmed presence of the plant, and the tips are general and do not replace the guidance of local services or a doctor.",
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


def build_prompt(lang, lat, lon, place_name, risk_percent, percentile, category, climate, land):
    titles = [g["title"] for g in TIP_GROUPS[lang]]
    if lang == "en":
        place_part = f", place: {place_name}" if place_name else ""
        cat_label = {"low": "lower", "medium": "medium", "high": "higher"}.get(category, "unknown")
        level_rule = {
            "low": "The index is lower. Keep the tone calm and light: general awareness and "
                   "routine observation, no urgency, and say nothing that suggests special measures are needed.",
            "medium": "The index is medium. Suggest moderate, targeted attention to typical places "
                      "and a sensible plan before the flowering season.",
            "high": "The index is higher. Suggest more attentive, prioritised actions: inspections "
                    "and planning ahead of the flowering season, still without alarm.",
        }.get(category, "Keep the tone cautious.")
        return (
            "Respond in English only.\n\n"
            "You are an assistant on an ecology website about common ragweed "
            "(Ambrosia artemisiifolia), an invasive plant, in Ukraine.\n"
            "A machine learning model estimated how similar the conditions in this area are to "
            f"places where ragweed has already been recorded (coordinates {lat}, {lon}{place_part}). "
            "This is a relative suitability index, not the probability that ragweed grows here.\n"
            f"- Index: {risk_percent}% (higher than {percentile}% of Ukraine's territory; "
            f"category: {cat_label})\n"
            f"- Mean temperature for the May-September season: "
            f"{num(climate.get('temp_mean'), 1, 'unknown')} °C\n"
            f"- Mean precipitation for the season: "
            f"{num(climate.get('precip_sum'), 1, 'unknown')} mm/day\n"
            f"- Mean humidity: {num(climate.get('humidity_mean'), 1, 'unknown')}%\n"
            f"- Share of cropland nearby: {pct(land.get('cropland'), 'unknown')}%\n"
            f"- Share of built-up land nearby: {pct(land.get('built'), 'unknown')}%\n\n"
            "Return ONLY a JSON object, with no markdown and no text around it, of this form:\n"
            '{"summary": "...", "groups": [{"items": ["...", "..."]}, {"items": ["...", "..."]}, '
            '{"items": ["...", "..."]}]}\n\n'
            "Rules:\n"
            "- summary: 1-2 short sentences for a general reader about what the result means and "
            "which conditions (climate, cropland, built-up share) may have influenced it. Do not "
            "claim that conditions promote or hold back the plant; only say what may have "
            "influenced the index.\n"
            f"- groups: exactly three, in this order: 1) {titles[0]}; 2) {titles[1]}; "
            f"3) {titles[2]}. Each has 2 items, one short sentence each (up to 20 words).\n"
            f"- {level_rule}\n"
            "- Tailor the tips to the data: if the share of cropland is high, give the farmers' "
            "group more specific points about field margins and fallow land; if the share of "
            "built-up land is high, give the municipal group more points about vacant lots, "
            "roadsides and construction sites; if both are small, keep tips brief and general. "
            "The three groups must not repeat each other.\n"
            "- Do not name herbicides, doses or chemical treatment. Medical advice is limited to "
            "at most one short phrase in the residents group (for example, to consult a doctor "
            "about symptoms); never name medications.\n"
            "- Never call the index a probability or say that ragweed is definitely present. "
            "Avoid words like \"extremely\", \"ideal\", \"guaranteed\". Do not use long dashes.\n"
            "- Do not add any disclaimer sentence; it is added separately."
        )

    place_part = f", місце: {place_name}" if place_name else ""
    cat_label = {"low": "нижча", "medium": "середня", "high": "вища"}.get(category, "невідома")
    level_rule = {
        "low": "Індекс нижчий. Тон спокійний і легкий: загальна обізнаність і звичайне спостереження, "
               "без терміновості, і нічого, що натякає на потребу особливих заходів.",
        "medium": "Індекс середній. Запропонуй помірну, цілеспрямовану увагу до типових місць "
                  "і розумний план перед сезоном цвітіння.",
        "high": "Індекс вищий. Запропонуй уважніші, пріоритетні дії: огляди та планування "
                "заздалегідь до сезону цвітіння, але без тривожного тону.",
    }.get(category, "Тон обережний.")
    return (
        "Відповідай лише українською мовою.\n\n"
        "Ти асистент екологічного сайту про інвазивну рослину амброзію полинолисту "
        "(Ambrosia artemisiifolia) в Україні.\n"
        "Модель машинного навчання оцінила, наскільки умови в цій місцевості схожі на ті, "
        f"де амброзію вже фіксували (координати {lat}, {lon}{place_part}). "
        "Це відносний індекс придатності, а не ймовірність того, що амброзія тут росте.\n"
        f"- Індекс: {dec(risk_percent, 'uk')}% (вище, ніж на {percentile}% території України; "
        f"категорія: {cat_label})\n"
        f"- Середня температура за сезон (травень-вересень): "
        f"{dec(num(climate.get('temp_mean')), 'uk')} °C\n"
        f"- Середні опади за сезон: {dec(num(climate.get('precip_sum')), 'uk')} мм/день\n"
        f"- Середня вологість: {dec(num(climate.get('humidity_mean')), 'uk')}%\n"
        f"- Частка ріллі в околі: {pct(land.get('cropland'))}%\n"
        f"- Частка забудови в околі: {pct(land.get('built'))}%\n\n"
        "Поверни ЛИШЕ JSON-об'єкт, без markdown і без тексту навколо, такого вигляду:\n"
        '{"summary": "...", "groups": [{"items": ["...", "..."]}, {"items": ["...", "..."]}, '
        '{"items": ["...", "..."]}]}\n\n'
        "Правила:\n"
        "- summary: 1-2 короткі речення для звичайної людини про те, що означає результат "
        "і які умови (клімат, частка ріллі, частка забудови) могли на нього вплинути. Не "
        "стверджуй, що умови сприяють рослині чи стримують її, лише що могло вплинути на індекс.\n"
        f"- groups: рівно три, у такому порядку: 1) {titles[0]}; 2) {titles[1]}; "
        f"3) {titles[2]}. У кожної по 2 пункти, по одному короткому реченню (до 20 слів).\n"
        f"- {level_rule}\n"
        "- Підлаштуй поради під дані: якщо частка ріллі висока, для аграріїв дай більш конкретні "
        "пункти про краї полів і перелоги; якщо висока частка забудови, для комунальних служб "
        "дай більше про пустирі, узбіччя й будмайданчики; якщо обидві малі, поради короткі й "
        "загальні. Групи не мають повторювати одна одну.\n"
        "- Не називай гербіциди, дози чи хімічну обробку. Медичні поради лише одна коротка "
        "фраза в групі мешканців (наприклад, із питань симптомів звернутися до лікаря), "
        "ліків не називай.\n"
        "- Ніколи не називай індекс ймовірністю і не стверджуй, що амброзія точно є. Не вживай "
        "слів «надзвичайно», «ідеальні», «гарантовано». Пиши грамотно, вживай «рілля», а не "
        "«пашня». Десяткові числа через кому. Не використовуй довгих тире.\n"
        "- Не додавай підсумкового застереження, воно додається окремо."
    )

def parse_llm_json(text, lang):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:]
    data = json.loads(text)
    summary = str(data["summary"]).strip()
    raw_groups = data["groups"]
    if not summary or len(raw_groups) != 3:
        raise ValueError("unexpected structure")
    titles = [g["title"] for g in TIP_GROUPS[lang]]
    groups = []
    for title, g in zip(titles, raw_groups):
        items = [str(x).strip() for x in g["items"] if str(x).strip()][:3]
        if not items:
            raise ValueError("empty group")
        groups.append({"title": title, "items": items})
    return summary, groups

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

    summary = None
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
            summary, groups = parse_llm_json(text, lang)
            break
        except Exception as e:
            last_error = str(e)
            summary = None
            time.sleep(2 * (attempt + 1))

    if summary is None:
        print(f"explain fallback: {last_error}")
        return jsonify({
            "explanation": fallback_explanation(
                lang, place_name, risk_percent, percentile, category, climate, land),
            "groups": TIP_GROUPS[lang] if category in ("medium", "high") else [],
            "closing": closing,
            "fallback": True,
        })

    return jsonify({"explanation": summary, "groups": groups, "closing": closing})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
