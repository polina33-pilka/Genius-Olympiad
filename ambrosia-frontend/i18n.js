const TRANSLATIONS = {
  uk: {
    brand: "🌿 AmbrosiaWatch",
    nav_home: "Головна",
    nav_problem: "Проблема",
    nav_map: "Карта",
    nav_methodology: "Методологія",
    hero_title: "Карта придатності територій для амброзії в Україні",
    hero_subtitle: "Модель машинного навчання оцінює, наскільки клімат і земля в місцевості схожі на ті, де амброзію полинолисту вже фіксували. Це допомагає визначити, де варто придивитися до небезпеки для здоров'я та екології.",
    hero_cta: "Переглянути карту",
    problem_title: "Чому це важливо",
    problem_health_title: "Здоров'я людей",
    problem_health_text: "Пилок амброзії — одна з найсильніших причин сезонної алергії та астми. Навіть невелика концентрація пилку викликає реакцію в чутливих людей.",
    problem_eco_title: "Екологічна шкода",
    problem_eco_text: "Амброзія витісняє місцеві види рослин, знижує родючість ґрунту і агресивно поширюється на порушених та покинутих землях.",
    problem_agri_title: "Сільське господарство",
    problem_agri_text: "Як бур'ян, амброзія знижує врожайність сільськогосподарських культур і вимагає додаткових витрат на боротьбу з нею.",
    map_title: "Інтерактивна карта",
    map_subtitle: "Кожна точка — комірка карти, для якої модель порахувала відносний індекс придатності (клімат 2015-2024 і частки пашні та забудови). Кольори відносні: нижні 50% точок зелені, наступні 30% помаранчеві, верхні 20% червоні.",
    legend_low: "Нижча",
    legend_medium: "Середня",
    legend_high: "Вища",
    search_title: "Перевірити конкретне місце",
    search_subtitle: "Введи назву міста чи села або просто клікни по карті — модель порахує індекс для цієї точки.",
    place_placeholder: "Місто або село, напр. Львів",
    place_button: "Знайти",
    manual_summary: "Ввести координати вручну",
    search_button: "Розрахувати",
    explain_button: "🤖 Пояснити простими словами",
    method_title: "Методологія",
    method_1: "Дані про спостереження амброзії взято з GBIF (Global Biodiversity Information Facility): лише спостереження людей за 2015-2024 роки, очищені за датою, координатами та точністю геолокації (до 5 км). Це близько 3100 записів у ~780 комірках 0.1°.",
    method_2: "Клімат (температура, опади, вологість за сезон травень-вересень, 2015-2024) отримано з Open-Meteo Historical Weather API. Частки пашні та забудови взято з ESA WorldCover 2020 і усереднено по комірках 0.1° (~10 км).",
    method_3: "Справжньої відсутності амброзії ми не знаємо, тому як порівняння використано фонові комірки: місця, де спостерігали інші рослини (GBIF), з імовірністю, пропорційною числу візитів. Так ми зменшуємо вплив того, що люди частіше фотографують у містах.",
    method_4: "Модель — Random Forest (500 дерев). Перевірка на регіонах, яких модель не бачила (просторова крос-валідація, блоки 2°): AUC-ROC ≈ 0.70.",
    method_5: "Для довільної точки бекенд у реальному часі отримує клімат, знаходить частки землі, рахує індекс і порівнює його з розподілом по території України. Категорії відносні: нижні 50% точок карти, наступні 30% та верхні 20%.",
    method_limitation: "Обмеження: це відносний індекс придатності, а не ймовірність наявності амброзії. Точність помірна (AUC ≈ 0.70). «Відсутність» у навчальних даних — лише фонові точки. Оцінка надійніша там, де багато спостерігачів, а в великих містах індекс може бути завищеним. Земля — знімок 2020 року; дороги та динаміка не враховані.",
    footer_text: "AmbrosiaWatch — оцінка придатності територій для амброзії полинолистої в Україні. Дані: GBIF · Open-Meteo · ESA WorldCover 2020 · © OpenStreetMap contributors",
    result_index: "Індекс придатності",
    result_percentile: "Вище, ніж на {n}% території України",
    result_land: "Земля в околі",
    land_cropland: "пашня",
    land_built: "забудова",
    result_note: "Відносний індекс: наскільки умови схожі на місця, де фіксували амброзію. Це не ймовірність її наявності.",
    result_place: "Місце",
    result_point: "Точка на карті",
    result_category_low: "нижча",
    result_category_medium: "середня",
    result_category_high: "вища",
    place_pick: "Знайдено кілька місць, обери потрібне:",
    place_not_found: "Місце не знайдено. Спробуй іншу назву.",
    place_error: "Не вдалось виконати пошук. Спробуй ще раз.",
    place_empty: "Введи назву місця.",
    error_fill_fields: "Будь ласка, введи коректні координати.",
    error_generic: "Сталася помилка. Спробуй ще раз.",
    error_outside_ukraine: "Ця точка поза Україною. Модель навчена на даних України, тому для таких місць результат не розраховується.",
    loading: "Розраховуємо...",
    searching: "Шукаємо..."
  },
  en: {
    brand: "🌿 AmbrosiaWatch",
    nav_home: "Home",
    nav_problem: "Problem",
    nav_map: "Map",
    nav_methodology: "Methodology",
    hero_title: "Ragweed Suitability Map for Ukraine",
    hero_subtitle: "A machine learning model estimates how similar the climate and land in an area are to places where common ragweed (Ambrosia artemisiifolia) has already been recorded. It helps show where to look more closely for health and ecological risks.",
    hero_cta: "View the map",
    problem_title: "Why it matters",
    problem_health_title: "Human health",
    problem_health_text: "Ragweed pollen is one of the strongest triggers of seasonal allergies and asthma. Even low pollen concentrations can cause reactions in sensitive people.",
    problem_eco_title: "Ecological damage",
    problem_eco_text: "Ragweed displaces native plant species, reduces soil fertility, and spreads aggressively on disturbed and abandoned land.",
    problem_agri_title: "Agriculture",
    problem_agri_text: "As a weed, ragweed reduces crop yields and requires additional costs to control.",
    map_title: "Interactive map",
    map_subtitle: "Each point is a map cell where the model computed a relative suitability index (2015-2024 climate plus the share of cropland and built-up land). Colours are relative: the lowest 50% of points are green, the next 30% orange, the top 20% red.",
    legend_low: "Lower",
    legend_medium: "Medium",
    legend_high: "Higher",
    search_title: "Check a specific location",
    search_subtitle: "Type a city or village name, or just click on the map — the model will compute the index for that point.",
    place_placeholder: "City or village, e.g. Lviv",
    place_button: "Search",
    manual_summary: "Enter coordinates manually",
    search_button: "Calculate",
    explain_button: "🤖 Explain in plain words",
    method_title: "Methodology",
    method_1: "Ragweed occurrence data comes from GBIF (Global Biodiversity Information Facility): human observations only, 2015-2024, cleaned by date, coordinates and geolocation precision (up to 5 km). That is about 3,100 records in ~780 cells of 0.1°.",
    method_2: "Climate (temperature, precipitation, humidity for the May-September season, 2015-2024) comes from the Open-Meteo Historical Weather API. Cropland and built-up shares come from ESA WorldCover 2020, averaged per 0.1° cell (~10 km).",
    method_3: "True absence of ragweed is unknown, so background cells are used for comparison: places where other plants were observed (GBIF), sampled in proportion to the number of observation visits. This reduces the effect of people photographing more often in cities.",
    method_4: "The model is a Random Forest (500 trees). Tested on regions it has not seen (spatial cross-validation, 2° blocks): AUC-ROC ≈ 0.70.",
    method_5: "For any point the backend fetches live climate, looks up the land shares, computes the index and compares it with the distribution across Ukraine. Categories are relative: the lowest 50% of map points, the next 30% and the top 20%.",
    method_limitation: "Limitations: this is a relative suitability index, not a probability that ragweed is present. Accuracy is moderate (AUC ≈ 0.70). Training 'absences' are only background points. Estimates are more reliable where many observers are active, and the index may be inflated in large cities. Land cover is a 2020 snapshot; roads and change over time are not included.",
    footer_text: "AmbrosiaWatch — assessment of territory suitability for common ragweed in Ukraine. Data: GBIF · Open-Meteo · ESA WorldCover 2020 · © OpenStreetMap contributors",
    result_index: "Suitability index",
    result_percentile: "Higher than {n}% of Ukraine's territory",
    result_land: "Land in the area",
    land_cropland: "cropland",
    land_built: "built-up",
    result_note: "Relative index: how similar conditions are to places where ragweed has been recorded. It is not a probability that it is present.",
    result_place: "Place",
    result_point: "Point on the map",
    result_category_low: "lower",
    result_category_medium: "medium",
    result_category_high: "higher",
    place_pick: "Several places found, pick the right one:",
    place_not_found: "Place not found. Try another name.",
    place_error: "Search failed. Please try again.",
    place_empty: "Please enter a place name.",
    error_fill_fields: "Please enter valid coordinates.",
    error_generic: "Something went wrong. Please try again.",
    error_outside_ukraine: "This point is outside Ukraine. The model was trained on Ukrainian data, so no result is calculated for such places.",
    loading: "Calculating...",
    searching: "Searching..."
  }
};

let currentLang = localStorage.getItem("lang") || "uk";

function applyTranslations() {
  const dict = TRANSLATIONS[currentLang];
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (dict[key]) el.textContent = dict[key];
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (dict[key]) el.placeholder = dict[key];
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
