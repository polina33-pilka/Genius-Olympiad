
const API_BASE_URL = "https://genius-olympiad.onrender.com";

const COLORS = { low: "#4caf50", medium: "#ff9800", high: "#e53935" };

let map;
let lastResult = null; // зберігаємо останній результат для кнопки "пояснити"

function initMap() {
  map = L.map("leaflet-map").setView([48.5, 31.5], 5.3);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 10,
  }).addTo(map);

  fetch(`${API_BASE_URL}/api/risk-map`)
    .then(r => r.json())
    .then(geojson => {
      geojson.features.forEach(f => {
        const [lon, lat] = f.geometry.coordinates;
        const cat = f.properties.risk_category;
        L.circleMarker([lat, lon], {
          radius: 4,
          fillColor: COLORS[cat] || "#999",
          color: COLORS[cat] || "#999",
          weight: 1,
          fillOpacity: 0.7,
        })
          .bindPopup(`${f.properties.risk_percent}% (${cat})`)
          .addTo(map);
      });
    })
    .catch(err => console.error("Не вдалось завантажити карту ризику:", err));
}

function showError(msg) {
  const box = document.getElementById("error-box");
  box.textContent = msg;
  box.classList.remove("hidden");
}

function hideError() {
  document.getElementById("error-box").classList.add("hidden");
}

function categoryLabel(cat) {
  const dict = TRANSLATIONS[currentLang];
  if (cat === "low") return dict.result_category_low;
  if (cat === "medium") return dict.result_category_medium;
  return dict.result_category_high;
}

async function handlePredict() {
  hideError();
  const latInput = document.getElementById("lat-input");
  const lonInput = document.getElementById("lon-input");
  const lat = parseFloat(latInput.value);
  const lon = parseFloat(lonInput.value);

  const dict = TRANSLATIONS[currentLang];

  if (isNaN(lat) || isNaN(lon)) {
    showError(dict.error_fill_fields);
    return;
  }

  const resultBox = document.getElementById("result-box");
  const resultMain = document.getElementById("result-main");
  const explainBtn = document.getElementById("explain-btn");
  const explainText = document.getElementById("explain-text");

  resultBox.classList.remove("hidden");
  resultMain.textContent = dict.loading;
  explainBtn.classList.add("hidden");
  explainText.classList.add("hidden");
  explainText.textContent = "";

  try {
    const resp = await fetch(`${API_BASE_URL}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon }),
    });
    const data = await resp.json();

    if (!resp.ok) {
      showError(data.error || dict.error_generic);
      resultBox.classList.add("hidden");
      return;
    }

    lastResult = { ...data, lat, lon };

    resultMain.innerHTML = `
      <strong>${dict.result_risk}: ${data.risk_percent}%</strong>
      <span style="color:${COLORS[data.risk_category]}"> (${categoryLabel(data.risk_category)})</span>
    `;
    explainBtn.classList.remove("hidden");
  } catch (err) {
    showError(dict.error_generic);
    resultBox.classList.add("hidden");
  }
}

async function handleExplain() {
  if (!lastResult) return;
  const explainText = document.getElementById("explain-text");
  const dict = TRANSLATIONS[currentLang];

  explainText.classList.remove("hidden");
  explainText.textContent = dict.loading;

  try {
    const resp = await fetch(`${API_BASE_URL}/api/explain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...lastResult, lang: currentLang }),
    });
    const data = await resp.json();

    if (!resp.ok) {
      explainText.textContent = data.error || dict.error_generic;
      return;
    }
    explainText.textContent = data.explanation;
  } catch (err) {
    explainText.textContent = dict.error_generic;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  document.getElementById("predict-btn").addEventListener("click", handlePredict);
  document.getElementById("explain-btn").addEventListener("click", handleExplain);
});
