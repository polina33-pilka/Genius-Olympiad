const API_BASE_URL = "https://genius-olympiad.onrender.com";
const NOMINATIM_URL = "https://nominatim.openstreetmap.org";
const OPEN_METEO_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search";

const COLORS = { low: "#4caf50", medium: "#ff9800", high: "#e53935" };

const FOREIGN_COUNTRIES = ["ro", "md", "pl", "sk", "hu", "by"];

const WAKE_HINT_MS = 5000;

const MAP_BOUNDS = [[42.5, 20.0], [54.0, 42.5]];

let map;
let selectedMarker = null;
let lastResult = null;
let requestCounter = 0;

function t(key) {
  return TRANSLATIONS[currentLang][key];
}

function categoryLabel(cat) {
  if (cat === "low") return t("result_category_low");
  if (cat === "medium") return t("result_category_medium");
  return t("result_category_high");
}

function showError(msg) {
  const box = document.getElementById("error-box");
  box.textContent = msg;
  box.classList.remove("hidden");
}

function hideError() {
  document.getElementById("error-box").classList.add("hidden");
}

function clearPlaceResults() {
  const list = document.getElementById("place-results");
  list.textContent = "";
  list.classList.add("hidden");
}

function uniqueJoin(parts) {
  const clean = parts.filter(Boolean);
  return clean.filter((p, i) => clean.indexOf(p) === i).join(", ");
}

function isInsideUkraine(lat, lon) {
  if (lat < 44.3 || lat > 52.4 || lon < 22.1 || lon > 40.3) return false;
  if (lat > 51.5 && (lon < 30.8 || lon > 33.3)) return false;
  if (lat > 52.0) return false;
  if (lon > 38.5 && lat > 49.5) return false;
  if (lon > 37.5 && lat > 50.5) return false;
  if (lon < 22.5 && lat > 49.6) return false;
  return true;
}

function initMap() {
  map = L.map("leaflet-map", {
    minZoom: 5,
    maxBounds: MAP_BOUNDS,
    maxBoundsViscosity: 0.8,
  }).setView([48.5, 31.5], 5.3);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 10,
  }).addTo(map);

  fetch(`${API_BASE_URL}/api/risk-map`)
    .then(r => r.json())
    .then(geojson => {
      geojson.features.forEach(f => {
        const [lon, lat] = f.geometry.coordinates;
        if (!isInsideUkraine(lat, lon)) return;
        const cat = f.properties.risk_category;
        L.circleMarker([lat, lon], {
          radius: 4,
          fillColor: COLORS[cat] || "#999",
          color: COLORS[cat] || "#999",
          weight: 1,
          fillOpacity: 0.7,
          interactive: false,
        }).addTo(map);
      });
    })
    .catch(err => console.error("Error loading risk map:", err));

  map.on("click", e => {
    const ll = e.latlng.wrap();
    runPrediction(ll.lat, ll.lng, null, false);
  });
}

function placeMarker(lat, lon, recenter) {
  if (selectedMarker) {
    selectedMarker.setLatLng([lat, lon]);
  } else {
    selectedMarker = L.circleMarker([lat, lon], {
      radius: 9,
      color: "#0d47a1",
      weight: 3,
      fillColor: "#2196f3",
      fillOpacity: 0.9,
    }).addTo(map);
  }
  if (recenter) {
    map.setView([lat, lon], Math.max(map.getZoom(), 7));
  }
}

async function reverseGeocode(lat, lon) {
  const url =
    `${NOMINATIM_URL}/reverse?lat=${lat}&lon=${lon}&zoom=13` +
    `&format=jsonv2&addressdetails=1&accept-language=${currentLang}`;
  const resp = await fetch(url);
  if (!resp.ok) return null;
  const data = await resp.json();
  const a = data.address;
  if (!a) return null;

  const name =
    a.city || a.town || a.village || a.hamlet || a.suburb ||
    a.municipality || a.county || a.state || "";
  if (!name) return null;

  return {
    name,
    label: uniqueJoin([name, a.county, a.state]),
    country: (a.country_code || "").toLowerCase(),
  };
}

async function searchNominatim(query) {
  const url =
    `${NOMINATIM_URL}/search?q=${encodeURIComponent(query)}` +
    `&countrycodes=ua&featureType=settlement&format=jsonv2` +
    `&addressdetails=1&limit=10&accept-language=${currentLang}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error("nominatim failed");
  const data = await resp.json();

  return data.map(r => {
    const a = r.address || {};
    const name =
      r.name || a.city || a.town || a.village || a.hamlet ||
      (r.display_name || "").split(",")[0];
    return {
      name,
      label: uniqueJoin([name, a.county || a.municipality || a.district, a.state]),
      lat: parseFloat(r.lat),
      lon: parseFloat(r.lon),
    };
  });
}

async function searchOpenMeteo(query) {
  const url =
    `${OPEN_METEO_GEO_URL}?name=${encodeURIComponent(query)}` +
    `&count=10&language=${currentLang}&format=json&countryCode=UA`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error("open-meteo geocoding failed");
  const data = await resp.json();

  return (data.results || [])
    .filter(r => !r.country_code || r.country_code === "UA")
    .map(r => ({
      name: r.name,
      label: uniqueJoin([r.name, r.admin2, r.admin1]),
      lat: r.latitude,
      lon: r.longitude,
    }));
}

async function runPrediction(lat, lon, placeName, recenter) {
  hideError();
  const myId = ++requestCounter;

  const resultBox = document.getElementById("result-box");
  const resultMain = document.getElementById("result-main");
  const explainBtn = document.getElementById("explain-btn");
  const explainText = document.getElementById("explain-text");

  resultBox.classList.remove("hidden");
  resultMain.textContent = t("loading");
  explainBtn.classList.add("hidden");
  explainText.classList.add("hidden");
  explainText.textContent = "";
  lastResult = null;

  if (!placeName) document.getElementById("place-input").value = "";
  placeMarker(lat, lon, recenter);

  let reversed = null;
  if (!placeName) {
    reversed = await reverseGeocode(lat, lon).catch(() => null);
    if (myId !== requestCounter) return;
    if (reversed && FOREIGN_COUNTRIES.includes(reversed.country)) {
      showError(t("error_outside_ukraine"));
      resultBox.classList.add("hidden");
      return;
    }
  }

  const wakeTimer = setTimeout(() => {
    if (myId === requestCounter && !lastResult) resultMain.textContent = t("waking");
  }, WAKE_HINT_MS);

  try {
    const resp = await fetch(`${API_BASE_URL}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon }),
    });
    const data = await resp.json();
    if (myId !== requestCounter) return;

    if (!resp.ok) {
      showError(data.error || t("error_generic"));
      resultBox.classList.add("hidden");
      return;
    }

    lastResult = { ...data, lat, lon, placeName: placeName || (reversed && reversed.label) || null };
    if (reversed) document.getElementById("place-input").value = reversed.name;
    renderResult();
    explainBtn.classList.remove("hidden");
  } catch (err) {
    if (myId !== requestCounter) return;
    showError(t("error_generic"));
    resultBox.classList.add("hidden");
  } finally {
    clearTimeout(wakeTimer);
  }
}

function renderResult() {
  if (!lastResult) return;
  const resultMain = document.getElementById("result-main");
  resultMain.textContent = "";

  const where = document.createElement("div");
  where.textContent = lastResult.placeName
    ? `${t("result_place")}: ${lastResult.placeName}`
    : `${t("result_point")}: ${lastResult.lat.toFixed(2)}, ${lastResult.lon.toFixed(2)}`;

  const risk = document.createElement("div");
  const strong = document.createElement("strong");
  strong.textContent = `${t("result_index")}: ${lastResult.risk_percent}%`;
  const cat = document.createElement("span");
  cat.style.color = COLORS[lastResult.risk_category];
  cat.textContent = ` (${categoryLabel(lastResult.risk_category)})`;
  risk.append(strong, cat);

  resultMain.append(where, risk);

  if (lastResult.percentile != null) {
    const pct = document.createElement("div");
    pct.textContent = t("result_percentile").replace("{n}", lastResult.percentile);
    resultMain.appendChild(pct);
  }
  if (lastResult.land) {
    const land = document.createElement("div");
    land.textContent =
      `${t("result_land")}: ${t("land_cropland")} ${Math.round(lastResult.land.cropland * 100)}%, ` +
      `${t("land_built")} ${Math.round(lastResult.land.built * 100)}%`;
    resultMain.appendChild(land);
  }
  if (lastResult.climate) {
    const c = lastResult.climate;
    const clim = document.createElement("div");
    clim.textContent = t("result_climate")
      .replace("{t}", Number(c.temp_mean).toFixed(1))
      .replace("{p}", Number(c.precip_sum).toFixed(1))
      .replace("{h}", Math.round(c.humidity_mean));
    resultMain.appendChild(clim);
  }
  const note = document.createElement("div");
  note.style.fontSize = "0.85rem";
  note.style.color = "#555";
  note.textContent = t("result_note");
  resultMain.appendChild(note);
}

function choosePlace(r) {
  document.getElementById("place-input").value = r.name;
  clearPlaceResults();
  runPrediction(r.lat, r.lon, r.label, true);
}

function showPlaceList(results) {
  const list = document.getElementById("place-results");
  list.textContent = "";

  const hint = document.createElement("div");
  hint.className = "place-hint";
  hint.textContent = t("place_pick");
  list.appendChild(hint);

  results.forEach(r => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "place-option";
    btn.textContent = r.label;
    btn.addEventListener("click", () => choosePlace(r));
    list.appendChild(btn);
  });

  list.classList.remove("hidden");
}

function mergeResults(primary, secondary) {
  const merged = [...primary];
  secondary.forEach(s => {
    const exists = merged.some(
      p => Math.abs(p.lat - s.lat) < 0.05 && Math.abs(p.lon - s.lon) < 0.05
    );
    if (!exists) merged.push(s);
  });
  return merged.slice(0, 12);
}

async function handlePlaceSearch() {
  hideError();
  clearPlaceResults();

  const query = document.getElementById("place-input").value.trim();
  if (!query) {
    showError(t("place_empty"));
    return;
  }

  const btn = document.getElementById("place-btn");
  btn.disabled = true;
  btn.textContent = t("searching");

  try {
    const [osm, meteo] = await Promise.allSettled([
      searchNominatim(query),
      searchOpenMeteo(query),
    ]);
    if (osm.status === "rejected" && meteo.status === "rejected") {
      throw new Error("both geocoders failed");
    }

    const results = mergeResults(
      osm.status === "fulfilled" ? osm.value : [],
      meteo.status === "fulfilled" ? meteo.value : []
    );

    if (results.length === 0) {
      showError(t("place_not_found"));
    } else if (results.length === 1) {
      choosePlace(results[0]);
    } else {
      showPlaceList(results);
    }
  } catch (err) {
    showError(t("place_error"));
  } finally {
    btn.disabled = false;
    btn.textContent = t("place_button");
  }
}

function handleManualPredict() {
  hideError();
  const lat = parseFloat(document.getElementById("lat-input").value);
  const lon = parseFloat(document.getElementById("lon-input").value);

  if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    showError(t("error_fill_fields"));
    return;
  }
  runPrediction(lat, lon, null, true);
}

async function handleExplain() {
  if (!lastResult) return;
  const explainText = document.getElementById("explain-text");

  explainText.classList.remove("hidden");
  explainText.textContent = t("loading");

  let done = false;
  const wakeTimer = setTimeout(() => {
    if (!done) explainText.textContent = t("waking");
  }, WAKE_HINT_MS);

  try {
    const resp = await fetch(`${API_BASE_URL}/api/explain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...lastResult, lang: currentLang }),
    });
    const data = await resp.json();
    done = true;

    if (!resp.ok) {
      explainText.textContent = data.error || t("error_generic");
      return;
    }
    explainText.textContent =
      data.explanation + (data.fallback ? "\n\n" + t("explain_fallback_note") : "");
  } catch (err) {
    explainText.textContent = t("error_generic");
  } finally {
    done = true;
    clearTimeout(wakeTimer);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initMap();

  document.getElementById("place-btn").addEventListener("click", handlePlaceSearch);
  document.getElementById("place-input").addEventListener("keydown", e => {
    if (e.key === "Enter") handlePlaceSearch();
  });
  document.getElementById("predict-btn").addEventListener("click", handleManualPredict);
  document.getElementById("explain-btn").addEventListener("click", handleExplain);

  document.getElementById("lang-toggle").addEventListener("click", () => {
    renderResult();
    clearPlaceResults();
  });
});
