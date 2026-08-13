# 🎯 НОВЫЕ ЦЕЛИ — Zero Markets + Yadix (разведка 2026-08-13)

**Метод:** DNS (dns.google), пассивный DNS (hackertarget), httpx/curl через SOCKS5-ротатор + HTTP-мост. Только GET/HEAD. Без эксплуатации.

---

## 1. ZERO MARKETS (zeromarkets.com) — ЖИВОЙ, за Cloudflare

### DNS
| Тип | Значение |
|---|---|
| A | 104.20.17.15, 172.66.144.218 (**Cloudflare**) |
| MX | zeromarkets-com.mail.protection.outlook.com (Microsoft 365) |
| SPF | ip4:168.245.178.40, 192.149.50.68 + Outlook + **AmazonSES + Mandrill + HubSpot** (маркетинг-стек) |
| NS | vin/kristina.ns.cloudflare.com |
| www | 301→www, WP-стек |

### Поддомены (29, из них 20+ НЕ за CF — реальные серверы)
| Группа | Хосты | IP | Что |
|---|---|---|---|
| **MT5-серверы** | tradeserver, demoserver, historyserver | **206.223.233.159/107/123** | Реальные MT5-серверы |
| **Резервные** | accessserver1/2, demoaccess, demobackup, historybackup, tradebackup | AWS (35.172.168.8, 44.210.232.235, 54.243.243.92, 98.87.215.43, 18.204.179.74, 52.7.6.150) | Торговые/резервные |
| **Кабинет** | client.zeromarkets.com | 99.84.160.77 (AWS, вне CF) | Клиентский кабинет |
| **Веб-трейдер** | trader.zeromarkets.com | 18.173.132.32 (AWS) | Веб-терминал (GTM-MTBX76FZ) |
| **Соцтрейдинг** | mt5-socialtrading, pamm, socialtrading-live/demo + ratings | 52.69.190.43 (AWS Tokyo) | PAMM/соцтрейдинг |
| **Мониторинг** | prometheus | 54.165.121.141 (AWS) | Prometheus |
| **Инструменты** | datatools, design | 185.158.133.1 | Вне CF |
| **Образование** | edu | 134.122.19.34 (DigitalOcean) | Edu-портал (200) |
| **Почта** | mail | 104.130.127.165 (вне CF) | Mail |
| **Внутренний** | ninedata | **10.0.1.107** | Внутренний IP в DNS! |
| CF-фронт | blog, campaign, cdncn, marketing, se | 104.20.17.15 / 172.66.144.218 | |

### Что открыто (проверено)
| Поверхность | Код | Статус |
|---|---|---|
| **wp-json/** | 200 | **REST API WordPress открыт** (namespaces: cf7, yoast, wp/v2) |
| wp-json/wp/v2/users | 302 | Закрыт (редирект) |
| wp-admin/ | 403 | Закрыт (CF-правило) |
| **tradeserver/terminal** | 200 | **MT5 WebTerminal открыт** |
| trader.zeromarkets.com | 200 | Веб-терминал (S3/HTML, GTM-MTBX76FZ) |
| blog | 200 | CF, живой |
| edu | 200 | DigitalOcean, живой |
| mail/datatools/client по IP | 000 | Недоступны с ротатора (firewall) |

### Стек
- WordPress + Yoast + Contact Form 7 + Elementor (13 локалей: en/ru/ko/fr/tr/de/it/ar/cn/mn/pk/ae/es/pt)
- robots.txt: мультиязычный, VPS-раздел (/tools/virtual-private-server-vps-for-forex-trading/)
- Аналитика: GTM, GA

---

## 2. YADIX (yadix.com) — ЖИВОЙ, НЕ за Cloudflare

### DNS
| Тип | Значение |
|---|---|
| A | **213.175.196.93** (brown.specialservers.com — SpecialServers, UK) |
| MX | Google Workspace (aspmx.l.google.com) |
| SPF | ip4:77.68.0.0/17, 77.68.3.192, 77.68.2.222, 77.68.2.83, 213.175.196.93 + Google + Outlook |
| NS | ns29/ns30.domaincontrol.com (GoDaddy) |

### Стек
- **Windows: Microsoft-IIS/10.0, ASP.NET 4.0.30319, PleskWin**
- GA: UA-31070774-1 (Universal Analytics)
- Все страницы 301 → / (георедирект IIS)

### Поддомены (10)
| Хост | IP | Что |
|---|---|---|
| **cabinet.yadix.com** | 77.68.2.222 | **Клиентский кабинет** (secure→cabinet 301) |
| secure, hft, id, asia | 3.33.251.168 (AWS Global Accelerator) | SSO/secure/HFT |
| ru | 15.197.225.128 (AWS us-west-2) | RU-локализация |
| indo | 77.68.3.192 | ID-локализация |
| cn | 156.247.9.251 | CN-локализация |
| demosocial | 87.117.223.5 | Демо соцтрейдинг |

### Что открыто (проверено)
| Поверхность | Код | Статус |
|---|---|---|
| **:8443** | **303 → /login.php** | **Панель входа на IIS (кастомная login.php) — ОТКРЫТА** |
| yadix.com (главная) | 200 | IIS/10.0, ASP.NET, Plesk |
| /bonus, /promotions, /register, /login, /partners | 301→/ | Георедирект |
| robots.txt | 404 | Нет |

---

## 3. ИТОГ — что открыто

### Zero Markets
1. **MT5-инфраструктура видна целиком** (tradeserver/demoserver/historyserver на 206.223.233.x) — терминал открыт
2. **WordPress REST API открыт** (wp-json 200) — перечисление контента/плагинов (CF7, Yoast)
3. Клиентский кабинет и соцтрейдинг — за пределами CF (AWS), но firewall закрывает с ротатора
4. Внутренний IP 10.0.1.107 в DNS (ninedata) — утечка внутренней сети

### Yadix
1. **Порт 8443 + /login.php — панель доступа открыта наружу** (не Plesk, кастомная login.php на IIS)
2. Windows/Plesk-стек на реальном IP — поверхность для атак на IIS/ASP.NET
3. Кабинет клиента (cabinet 77.68.2.222) — вне CF

## 4. АРТЕФАКТЫ
- output/zeromarkets_subdomains.txt (29), yadix_subdomains.txt (10)
- edge_check.txt (пограничные: trading.md — агрегатор, fxgrow/fxclub — легальные, ftm.by — блочит)
