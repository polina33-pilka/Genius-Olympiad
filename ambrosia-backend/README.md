# Ambrosia Risk Backend

Flask-бекенд: приймає координати, качає клімат з Open-Meteo, прогнозує ризик
через навчену модель, і генерує пояснення через Gemini.

## Деплой на Render (покроково)

1. Завантаж цю папку (`ambrosia-backend`) як окремий репозиторій на GitHub.
2. Зайди на https://render.com → New → Web Service.
3. Підключи свій GitHub-репозиторій.
4. Налаштування:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Environment:** Python 3
5. У розділі **Environment Variables** додай:
   - `GEMINI_API_KEY` — твій ключ з https://aistudio.google.com/apikey
   - `FRONTEND_ORIGIN` — адреса твого фронтенду після деплою (напр. `https://ambrosiawatch.netlify.app`), або залиш `*` для тестів.
6. Натисни **Create Web Service** — Render сам збере і задеплоїть.
7. Після деплою отримаєш адресу типу `https://ambrosia-backend-xxxx.onrender.com`.
   Скопіюй її — вона знадобиться для фронтенду (`API_BASE_URL` у `script.js`).

## Локальний запуск (для перевірки перед деплоєм)

```bash
cd ambrosia-backend
pip install -r requirements.txt
set GEMINI_API_KEY=твій_ключ   (Windows: $env:GEMINI_API_KEY="твій_ключ")
python app.py
```

Сервер буде доступний на `http://localhost:5000`.

## Ендпоінти

- `GET /api/health` — перевірка, що сервер живий.
- `GET /api/risk-map` — повертає готову GeoJSON-карту (1852 точки).
- `POST /api/predict` — `{"lat": 49.8, "lon": 24.0}` → ризик для цієї точки.
- `POST /api/explain` — пояснення результату через Gemini (потребує `GEMINI_API_KEY`).

## Важливо

- Безкоштовний тариф Render "засинає" після 15 хв без запитів — перший запит
  після сну займає 30-60 сек. Перед демонстрацією/захистом зроби один тестовий
  запит заздалегідь, щоб "розбудити" сервер.
- `scikit-learn` версія в `requirements.txt` (1.5.1) має співпадати з версією,
  якою навчалась модель — якщо в тебе локально інша версія, онови рядок під себе.
