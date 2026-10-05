# Ambrosia Risk Frontend

Статичний сайт: головна, проблема, інтерактивна карта, методологія,
пошук ризику по координатах, переключення мови UA/EN.

## Деплой на Netlify (покроково)

1. Зайди на https://netlify.com → Add new site → Import an existing project.
2. Підключи свій GitHub-репозиторій.
3. У налаштуваннях вкажи **Base directory**: `ambrosia-frontend`
4. Build command залиш порожнім (статичний сайт, збірка не потрібна).
5. Publish directory: `ambrosia-frontend` (або залиш за замовчуванням, якщо Base directory вже вказано).
6. Deploy site.

## Альтернатива — GitHub Pages

1. У репозиторії: Settings → Pages → Source → гілка `main`, папка `/ambrosia-frontend`.
2. Сайт зʼявиться на `https://<твій-юзернейм>.github.io/<репозиторій>`.

## Після деплою

Бекенд уже задеплоєно на Render: https://genius-olympiad.onrender.com
Адреса вже вписана у `script.js`.
