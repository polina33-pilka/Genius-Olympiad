const TRANSLATIONS = {
  uk: {
    brand: "🌿 AmbrosiaWatch",
    nav_home: "Головна",
    nav_problem: "Проблема",
    nav_map: "Карта",
    nav_methodology: "Методологія",
    hero_title: "Карта ризику поширення амброзії в Україні",
    hero_subtitle: "Модель машинного навчання оцінює ймовірність присутності амброзії полинолистої на основі кліматичних умов — допомагає передбачити зони ризику для здоров'я та екології.",
    hero_cta: "Переглянути карту",
    problem_title: "Чому це важливо",
    problem_health_title: "Здоров'я людей",
    problem_health_text: "Пилок амброзії — одна з найсильніших причин сезонної алергії та астми. Навіть невелика концентрація пилку викликає реакцію в чутливих людей.",
    problem_eco_title: "Екологічна шкода",
    problem_eco_text: "Амброзія витісняє місцеві види рослин, знижує родючість ґрунту і агресивно поширюється на порушених та покинутих землях.",
    problem_agri_title: "Сільське господарство",
    problem_agri_text: "Як бур'ян, амброзія знижує врожайність сільськогосподарських культур і вимагає додаткових витрат на боротьбу з нею.",
    map_title: "Інтерактивна карта ризику",
    map_subtitle: "Кожна точка — розрахункова комірка (~28 км), для якої модель оцінила ризик на основі клімату 2015-2024 рр.",
    legend_low: "Низький",
    legend_medium: "Середній",
    legend_high: "Високий",
    search_title: "Перевірити конкретне місце",
    search_subtitle: "Введи координати (широта, довгота) — модель порахує ризик для цієї точки в реальному часі.",
    search_button: "Розрахувати ризик",
    explain_button: "🤖 Пояснити простими словами",
    method_title: "Методологія",
    method_1: "Дані про спостереження амброзії зібрані з GBIF (Global Biodiversity Information Facility), очищені за датою, координатами та точністю геолокації.",
    method_2: "Кліматичні дані (температура, опади, вологість за сезон травень-вересень, 2015-2024) отримані через Open-Meteo Historical Weather API.",
    method_3: "Для навчання моделі використано збалансований набір: точки присутності виду (presence) та випадково згенеровані фонові точки (pseudo-absence) в межах області спостережень.",
    method_4: "Модель — Random Forest Classifier (300 дерев), навчена та перевірена через 5-fold крос-валідацію (AUC-ROC ≈ 0.71).",
    method_5: "Для довільної точки на карті бекенд у реальному часі отримує кліматичні дані та прогнозує ризик за допомогою цієї моделі.",
    method_limitation: "Обмеження: модель враховує лише кліматичні фактори. Реальне поширення виду залежить також від типу землекористування, транспортних шляхів та діяльності людини — це напрямок для подальшого вдосконалення моделі.",
    footer_text: "Проєкт створено для Genius Olympiad — AI для розв'язання екологічних проблем.",
    result_risk: "Ризик",
    result_category_low: "низький",
    result_category_medium: "середній",
    result_category_high: "високий",
    error_fill_fields: "Будь ласка, введи коректні координати.",
    error_generic: "Сталася помилка. Спробуй ще раз.",
    loading: "Розраховуємо..."
  },
  en: {
    brand: "🌿 AmbrosiaWatch",
    nav_home: "Home",
    nav_problem: "Problem",
    nav_map: "Map",
    nav_methodology: "Methodology",
    hero_title: "Ragweed Spread Risk Map for Ukraine",
    hero_subtitle: "A machine learning model estimates the likelihood of common ragweed (Ambrosia artemisiifolia) based on climate conditions — helping anticipate risk zones for public health and ecology.",
    hero_cta: "View the map",
    problem_title: "Why it matters",
    problem_health_title: "Human health",
    problem_health_text: "Ragweed pollen is one of the strongest triggers of seasonal allergies and asthma. Even low pollen concentrations can cause reactions in sensitive people.",
    problem_eco_title: "Ecological damage",
    problem_eco_text: "Ragweed displaces native plant species, reduces soil fertility, and spreads aggressively on disturbed and abandoned land.",
    problem_agri_title: "Agriculture",
    problem_agri_text: "As a weed, ragweed reduces crop yields and requires additional costs to control.",
    map_title: "Interactive risk map",
    map_subtitle: "Each point is a computed grid cell (~28 km) where the model estimated risk based on 2015-2024 climate data.",
    legend_low: "Low",
    legend_medium: "Medium",
    legend_high: "High",
    search_title: "Check a specific location",
    search_subtitle: "Enter coordinates (latitude, longitude) — the model will compute the risk for that point in real time.",
    search_button: "Calculate risk",
    explain_button: "🤖 Explain in plain words",
    method_title: "Methodology",
    method_1: "Ragweed occurrence data was collected from GBIF (Global Biodiversity Information Facility), cleaned by date, coordinates, and geolocation precision.",
    method_2: "Climate data (temperature, precipitation, humidity for the May-September season, 2015-2024) was obtained via the Open-Meteo Historical Weather API.",
    method_3: "Model training used a balanced dataset: presence points and randomly generated background (pseudo-absence) points within the observed area.",
    method_4: "The model is a Random Forest Classifier (300 trees), trained and validated via 5-fold cross-validation (AUC-ROC ≈ 0.71).",
    method_5: "For any point on the map, the backend fetches live climate data and predicts risk using this model.",
    method_limitation: "Limitation: the model only accounts for climate factors. Real-world species spread also depends on land use, roads, and human activity — a direction for future improvement.",
    footer_text: "Built for Genius Olympiad — AI for environmental problem solving.",
    result_risk: "Risk",
    result_category_low: "low",
    result_category_medium: "medium",
    result_category_high: "high",
    error_fill_fields: "Please enter valid coordinates.",
    error_generic: "Something went wrong. Please try again.",
    loading: "Calculating..."
  }
};

let currentLang = localStorage.getItem("lang") || "uk";

function applyTranslations() {
  const dict = TRANSLATIONS[currentLang];
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (dict[key]) el.textContent = dict[key];
  });
  document.documentElement.lang = currentLang;
}

function toggleLang() {
  currentLang = currentLang === "uk" ? "en" : "uk";
  localStorage.setItem("lang", currentLang);
  applyTranslations();
}

document.addEventListener("DOMContentLoaded", () => {
  applyTranslations();
  document.getElementById("lang-toggle").addEventListener("click", toggleLang);
});
