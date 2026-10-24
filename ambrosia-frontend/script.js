const API_BASE_URL = "https://genius-olympiad.onrender.com";
const NOMINATIM_URL = "https://nominatim.openstreetmap.org";
const OPEN_METEO_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search";

const COLORS = { low: "#4caf50", medium: "#ff9800", high: "#e53935" };

const FOREIGN_COUNTRIES = ["ro", "md", "pl", "sk", "hu", "by", "ru"];

const WAKE_HINT_MS = 5000;

const MAP_BOUNDS = [[43.0, 20.5], [53.5, 42.0]];
const UKRAINE_VIEW = [[44.2, 22.0], [52.5, 40.4]];
const BORDER_TOLERANCE = 0.07;

const UKRAINE_POLYGON = [
  [31.785998, 52.101678], [32.159412, 52.061267], [32.412058, 52.288695], [32.715761, 52.238465],
  [33.7527, 52.335075], [34.391731, 51.768882], [34.141978, 51.566413], [34.224816, 51.255993],
  [35.022183, 51.207572], [35.377924, 50.773955], [35.356116, 50.577197], [36.626168, 50.225591],
  [37.39346, 50.383953], [38.010631, 49.915662], [38.594988, 49.926462], [40.069058, 49.601055],
  [40.080789, 49.30743], [39.674664, 48.783818], [39.895632, 48.232405], [39.738278, 47.898937],
  [38.770585, 47.825608], [38.255112, 47.5464], [38.223538, 47.10219], [37.425137, 47.022221],
  [36.759855, 46.6987], [35.823685, 46.645964], [34.962342, 46.273197], [35.020788, 45.651219],
  [35.510009, 45.409993], [36.529998, 45.46999], [36.334713, 45.113216], [35.239999, 44.939996],
  [33.882511, 44.361479], [33.326421, 44.564877], [33.546924, 45.034771], [32.454174, 45.327466],
  [32.630804, 45.519186], [33.588162, 45.851569], [33.298567, 46.080598], [31.74414, 46.333348],
  [31.675307, 46.706245], [30.748749, 46.5831], [30.377609, 46.03241], [29.603289, 45.293308],
  [29.149725, 45.464925], [28.679779, 45.304031], [28.233554, 45.488283], [28.485269, 45.596907],
  [28.659987, 45.939987], [28.933717, 46.25883], [28.862972, 46.437889], [29.072107, 46.517678],
  [29.170654, 46.379262], [29.759972, 46.349988], [30.024659, 46.423937], [29.83821, 46.525326],
  [29.908852, 46.674361], [29.559674, 46.928583], [29.415135, 47.346645], [29.050868, 47.510227],
  [29.122698, 47.849095], [28.670891, 48.118149], [28.259547, 48.155562], [27.522537, 48.467119],
  [26.857824, 48.368211], [26.619337, 48.220726], [26.19745, 48.220881], [25.945941, 47.987149],
  [25.207743, 47.891056], [24.866317, 47.737526], [24.402056, 47.981878], [23.760958, 47.985598],
  [23.142236, 48.096341], [22.710531, 47.882194], [22.64082, 48.15024], [22.085608, 48.422264],
  [22.280842, 48.825392], [22.558138, 49.085738], [22.776419, 49.027395], [22.51845, 49.476774],
  [23.426508, 50.308506], [23.922757, 50.424881], [24.029986, 50.705407], [23.527071, 51.578454],
  [24.005078, 51.617444], [24.553106, 51.888461], [25.327788, 51.910656], [26.337959, 51.832289],
  [27.454066, 51.592303], [28.241615, 51.572227], [28.617613, 51.427714], [28.992835, 51.602044],
  [29.254938, 51.368234], [30.157364, 51.416138], [30.555117, 51.319503], [30.619454, 51.822806],
  [30.927549, 52.042353], [31.785998, 52.101678],
];

let map;
let selectedMarker = null;
let lastResult = null;
let requestCounter = 0;

function t(key) {
  return TRANSLATIONS[currentLang][key];
}

function formatNumber(value) {
  const text = String(value);
  return currentLang === "uk" ? text.replace(".", ",") : text;
}

const ERROR_KEYS = {
  invalid_coords: "error_fill_fields",
  no_land_data: "error_no_land",
  climate_failed: "error_climate",
};

function apiErrorMessage(data) {
  const key = data && data.code ? ERROR_KEYS[data.code] : null;
  return t(key || "error_generic");
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

const TRANSLIT = {
  а: "a", б: "b", в: "v", г: "h", ґ: "g", д: "d", е: "e", є: ["ye", "ie"],
  ж: "zh", з: "z", и: "y", і: "i", ї: ["yi", "i"], й: ["y", "i"], к: "k",
  л: "l", м: "m", н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u",
  ф: "f", х: "kh", ц: "ts", ч: "ch", ш: "sh", щ: "shch", ь: "",
  ю: ["yu", "iu"], я: ["ya", "ia"],
};

const WORD_MAP = {
  "міська": "Urban",
  "селищна": "Settlement",
  "сільська": "Rural",
  "громада": "Hromada",
  "район": "Raion",
  "область": "Oblast",
};

function translitWord(word) {
  const mapped = WORD_MAP[word.toLowerCase()];
  if (mapped) return mapped;

  let out = "";
  for (let i = 0; i < word.length; i++) {
    const ch = word[i];
    const lower = ch.toLowerCase();
    if (lower === "'" || lower === "’" || lower === "ʼ") continue;

    let rep = TRANSLIT[lower];
    if (rep === undefined) {
      out += ch;
      continue;
    }
    const start = i === 0 || word[i - 1] === "-";
    if (Array.isArray(rep)) rep = start ? rep[0] : rep[1];
    if (lower === "г" && i > 0 && word[i - 1].toLowerCase() === "з") rep = "gh";
    if (ch !== lower && rep) rep = rep[0].toUpperCase() + rep.slice(1);
    out += rep;
  }
  return out;
}

function toLatin(text) {
  if (currentLang !== "en" || !text || !/[\u0400-\u04FF]/.test(text)) return text;
  return text.replace(/[\u0400-\u04FF][\u0400-\u04FF'’ʼ-]*/g, translitWord);
}

function uniqueJoin(parts) {
  const clean = parts.filter(Boolean).map(toLatin);
  return clean.filter((p, i) => clean.indexOf(p) === i).join(", ");
}

function distToSegment(px, py, ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  const len2 = dx * dx + dy * dy;
  let k = len2 === 0 ? 0 : ((px - ax) * dx + (py - ay) * dy) / len2;
  k = Math.max(0, Math.min(1, k));
  return Math.hypot(px - (ax + k * dx), py - (ay + k * dy));
}

function isInsideUkraine(lat, lon) {
  const n = UKRAINE_POLYGON.length;
  let inside = false;
  let minDist = Infinity;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const [xi, yi] = UKRAINE_POLYGON[i];
    const [xj, yj] = UKRAINE_POLYGON[j];
    if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
    minDist = Math.min(minDist, distToSegment(lon, lat, xi, yi, xj, yj));
  }
  return inside || minDist < BORDER_TOLERANCE;
}

function initMap() {
  map = L.map("leaflet-map", {
    minZoom: 5,
    zoomSnap: 0.1,
    maxBounds: MAP_BOUNDS,
    maxBoundsViscosity: 0.8,
  });
  map.fitBounds(UKRAINE_VIEW, { padding: [8, 8] });
  map.createPane("selectedPane");
  map.getPane("selectedPane").style.zIndex = 650;

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
      pane: "selectedPane",
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
    name: toLatin(name),
    label: uniqueJoin([name, a.county, a.state]),
    country: (a.country_code || "").toLowerCase(),
  };
}

async function searchNominatim(query) {
  const url =
    `${NOMINATIM_URL}/search?q=${encodeURIComponent(query)}` +
    `&countrycodes=ua&featureType=settlement&format=jsonv2` +
    `&addressdetails=1&namedetails=1&limit=10&accept-language=${currentLang}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error("nominatim failed");
  const data = await resp.json();

  return data.map(r => {
    const a = r.address || {};
    const nd = r.namedetails || {};
    const name =
      nd[`name:${currentLang}`] ||
      a.city || a.town || a.village || a.hamlet ||
      r.name ||
      (r.display_name || "").split(",")[0];
    return {
      name: toLatin(name),
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
      name: toLatin(r.name),
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
      showError(apiErrorMessage(data));
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
  strong.textContent = `${t("result_index")}: ${formatNumber(lastResult.risk_percent)}%`;
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
      .replace("{t}", formatNumber(Number(c.temp_mean).toFixed(1)))
      .replace("{p}", formatNumber(Number(c.precip_sum).toFixed(1)))
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
  const merged = [];
  const hasLabel = r =>
    merged.some(p => p.label.toLowerCase() === r.label.toLowerCase());

  primary.forEach(r => {
    if (!hasLabel(r)) merged.push(r);
  });
  secondary.forEach(r => {
    const near = merged.some(
      p => Math.abs(p.lat - r.lat) < 0.05 && Math.abs(p.lon - r.lon) < 0.05
    );
    if (!near && !hasLabel(r)) merged.push(r);
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
    if (!done) explainText.textContent = t("waking_explain");
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
      explainText.textContent = apiErrorMessage(data);
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
