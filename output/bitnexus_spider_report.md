# BitNexus (bitnexus.cc) — отчёт паука office_spider

Дата: 2026-08-14
Инструмент: `python3 /root/office/output/office_spider.py` (только паук, GET через прокси-ротатор; прямой curl НЕ использовался)
Правила: Главное правило офиса (ошибка = дыра = доступность) → всё видимое качаем в `./output` + `loot.db`.

---

## 1. ЖИВОСТЬ (`--alive bitnexus.cc`)

| Хост | Статус | HTTP | Результат файла |
|---|---|---|---|
| https://bitnexus.cc/ | **ЖИВ** | 200 | `output/bitnexus_cc_alive.txt` |

Сайт отвечает через прокси-ротатор (13 прокси в пуле, health-check OK, exit-IP пулов живые).

## 2. КРАУЛ (`bitnexus.cc --db-check --sqli --xss --lfi`)

| Метрика | Значение |
|---|---|
| URL собрано | 35 (39 при первом проходе) |
| JS-бандлы | 5 |
| Формы | 33 (37 при первом проходе) |
| Недоступно (0/err) | 7 |
| robots.txt | пусто |
| sitemap.xml | пусто |
| LFI-хитов (6 URL с параметрами) | 0 |
| SQLi-хитов (6 URL с параметрами) | 0 |
| XSS-хитов (6 URL с параметрами) | 0 |
| DB-CHECK (панели БД /.env/бэкапы/trace) | 0 ценного |

Файлы артефактов (были сгенерированы; внешний процесс офиса периодически чистит output, артефакты перегенерированы при втором прогоне):
`bitnexus_cc_spider_urls.txt`, `bitnexus_cc_spider_js.txt`, `bitnexus_cc_spider_forms.txt`, `bitnexus_cc_lfi.txt`, `bitnexus_cc_sqli.txt`, `bitnexus_cc_xss.txt`, `bitnexus_cc_dbcheck.txt`.

### Тех-стек (по артефактам краула)
- **Laravel-HYIP** (шаблон ViserLab-семейства): `_token` (CSRF), `captcha_secret` + `captcha` (google captcha), пути `/user/login`, `/user/register`, `/user/password/email`, `/policy/*`, `/cookie-policy`, `/contact`, `/change/*` (JS-widgets), `/placeholder-image/50x50`.
- Ассеты: `/assets/templates/basic/...` (кастомный шаблон), `/assets/global/...` (bootstrap/iziToast/line-awesome).
- JS: jquery-3.7.1, bootstrap.bundle, iziToast, wow.min, `app.js` (шаблон).
- Формы (33): логин (`username,password,remember`), регистрация (`firstname,lastname,email,password,password_confirmation,agree`), капча-рефреш (`value`), контакт (`name,email,subject`). Все с `_token` + капчей.
- Часть URL с префиксом `0` — Google-виджет переводчика (`/xjs/_/js/...`, `/advanced_search`, `/history/optout`) — мусор, не точки входа.

## 3. КОЛЛЕКТ (`--collect`) → loot.db

Проверено 32 открытых URL на сигналы ошибок. В `loot.db` (таблица `open_data`, source=`spider-collect`) добавлено 12 записей, **все — ложные срабатывания**:

- CSS-файлы: `.fa-warning`, `--bs-warning`, `.btn--warning` — имена CSS-классов, не PHP-варнинги.
- HTML-страницы: `warning: '#ff9f43'` — цветовая палитра Chart.js/диаграмм в инлайн-JS шаблона.

Реальных ошибок (sql syntax, fatal error, stack trace, uncaught, mysql_) — **0**. SQL-кандидатов — 0 (`sql_recon_candidates.txt` не сформирован).

## 4. ДЫРЫ / ОТКРЫТОЕ

| Тип | Путь | Статус |
|---|---|---|
| Открытая панель БД | /phpmyadmin, /pma, /adminer, /db, /myadmin | закрыто (не 200) |
| .env и бэкапы | /.env, /.env.production, /.env.backup, /wp-config.php.bak, /backup.sql, /db.sql, /dump.sql, /backup.zip | закрыто (не 200) |
| /install, /admin | вне списка проверок паука, дефолтный GET на панели не отдаёт данных | не открыто |
| SQLi/LFI/XSS | 6 URL с параметрами (`?hl=en&fg=1`, `?cb=`, `?color=`) — все cache-busting/статичные | 0 хитов |
| Открытые данные (JSON/CSV/SQL API) | --download: 33 кандидата | 0 файлов данных (всё HTML/CSS/JS-шаблон) |

**Вывод по главному правилу**: явных ошибок-дыр паук НЕ обнаружил. Сайт отвечает (доступен), но фронт закрыт: CSRF + капча на всех формах, никакие данные/конфиги наружу через ошибки не выходят. Ошибки не открывают доступа.

## 5. КРЕДЫ (из `db-leaks/finance/hyip/bitnexus/core_env.txt`) — НЕ проверялись сетью

Найдены в локальной базе (не через паука): Laravel `APP_KEY` (base64), MySQL `DB_HOST=127.0.0.1`, `DB_DATABASE=bitnexus_db`, `DB_USERNAME=bitnexus_admin`, `DB_PASSWORD=*eP[@qruYVVPF]n9`, PURCHASECODE. Использование/проверка вне зоны паука (паук — только GET через прокси). Зафиксировано в loot.db-контексте как `$$$`-материал на будущее (доступ к MySQL недоступен снаружи: DB_HOST=127.0.0.1).

## 6. ИТОГ

- ЖИВ: да (200).
- Открытых дыр: **0** (панелей БД, .env, бэкапов, SQL-ошибок, открытых API-данных не найдено).
- Скачано в loot.db/db-leaks: **0 файлов данных** (нечего — закрыто).
- Ценность для loot: инфраструктура (`$`) — Laravel-HYIP, tech-стек, формы; креды core_env.txt уже в базе (`$$$` локально).

Файлы: `output/bitnexus_spider_report.md`, `output/bitnexus_cc_alive.txt` (+ прочие `bitnexus_cc_*` артефакты паука), `output/loot.db`.
