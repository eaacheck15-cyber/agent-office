# 🎯 QUOMARKETS (quomarkets.com) — ГЛУБОКИЙ АНАЛИЗ (2026-08-13)

**Статус:** активный · **Тип:** скам-брокер (офшорные «лицензии») · **За CF:** Cloudflare
**Метод:** разведка через SOCKS5-ротатор (127.0.0.1:1080) + HTTP-мост, DNS-пассивка. Только GET/HEAD.

---

## 1. ИНФРАСТРУКТУРА

| Параметр | Значение |
|---|---|
| A (фронт) | 172.66.40.75 / 172.66.43.181 — **Cloudflare** |
| NS | armando/indie.ns.cloudflare.com |
| MX | quomarkets-com.mail.protection.outlook.com (**Microsoft 365**) |
| SPF | 9 сервисов: zendesk, mailjet, outlook, mlsend, zeptomail, google, zoho, getresponse, hostedemail |
| Юрлицо (сертификаты) | **Process Automation Ltd.** (O=), wildcard `*.quomarkets.com` |
| Сертификат | Google Trust Services, 07.07.2026 → 05.10.2026, TLSv1.3 AES-256-GCM |
| HSTS | **ОТСУТСТВУЕТ** |

### Реальные IP за CF (найдены)
| Хост | IP | Что это |
|---|---|---|
| register.quomarkets.com | **3.227.143.66** (AWS us-east-1) | Rebrandly-редирект-движок (engine: Rebrandly.redirect v2.1), :80 Squid/4.10 |
| sp-track/sp-bounce | 54.92.251.90 (AWS) | SendX email-трекинг (track.sx27.email) |
| link | CNAME→track.smtp2go.net | SMTP2GO |
| fwtrack | CNAME→fmsendcrmclick.eu (AWS eu-central) | FreshMail CRM |
| support | CNAME→quomarkets.zendesk.com (216.198.53.6) | Zendesk |
| 51.68.54.184 (OVH) | исторический traefik | **Хонейпот/заброшен**: фейковые баннеры Apache Mandrake 2004 / TP-Link / IPG8000 |

## 2. ПОДДОМЕНЫ (37)

api, api-auth, apiv2, biztech, blik, bucket, calc, checkout, eur-checkout, fwtrack, go, ibtools, id,
leaderboard, link, mediashare, my, myv2, portainer, presentations, r2, rabbitmq, register, sandbox,
social, sp-bounce, sp-track, sso, status, support, tradingview, traefik, tyga, uploads, webtrader, www

## 3. ЖИВЫЕ ЗОНЫ (код + что это)

| Хост | Код | Что |
|---|---|---|
| www.quomarkets.com | 200 | WordPress+Elementor+Yoast, 13 языков, георедирект Geo Targetly |
| **rabbitmq.quomarkets.com** | **200** | **RabbitMQ Management консоль открыта** (allow HEAD/GET, OPTIONS) |
| **api-auth.quomarkets.com** | 200 | **squid/4.10 proxy** |
| **biztech.quomarkets.com** | 401 | бизнес-портал (нужна авторизация) |
| **portainer/traefik** | 501 | Docker/Traefik-панели за баннером-обманкой |
| **my.quomarkets.com** | 200 | Клиентский портал: Angular SPA, **FlexProtect "b2copy"**, Ory IdP, Zendesk+Intercom |
| api.quomarkets.com | 302→/auth/login | API-шлюз `/api/v2/*` |
| register.quomarkets.com | 302 (Rebrandly) | AWS ALB 3.227.143.66, Laravel |
| go.quomarkets.com | 200 | Реферальная («Go \| QuoMarkets») |
| ibtools.quomarkets.com | 200 | **IBTools** (SiteGround) — инструменты IB |
| id / sso | 301/нет | SSO-кластер |
| checkout / eur-checkout / blik | 301/503/- | платёжки (BLIK — Польша) |
| webtrader.quomarkets.com | 400 | веб-терминал |
| status (StatusCake), tradingview (лицензия), social (→/portal), leaderboard (→widgets) | 200/302 | сервисы |

## 4. ОТКРЫТЫЕ ЭНДПОИНТЫ / УТЕЧКИ

1. **`GET https://api.quomarkets.com/api/v2/my/system-info` — 200 БЕЗ авторизации**:
   - tenant `quomarkets`, вендор **FlexProtect**, Zendesk channel ID (base64→tradequo.zendesk.com)
   - iOS app: `apps.apple.com/bj/app/quomarkets/id6741915436`
   - APK: `android.flexdns.tech/api/v1/stable/01937847-912d-7a16-8ce0-48dd9d1c35cc`
   - Amplitude-ключ: `954944e604e32924a60b4dda9830d6f0`
2. **CORS-мисконфиг**: `access-control-allow-origin: *` + `access-control-allow-credentials: true` (WP)
3. **HSTS отсутствует** (все хосты)
4. `wp-json/wp/v2/users` → 401 (перечисление закрыто, но REST открыт)
5. `/api/v2/backoffice/tenants/` → 404 (бэк-офис существует)
6. `apiv2` → 501 Apache-AdvancedExtranetServer/2.0.44 (Mandrake) — фейковый баннер
7. robots.txt — **копия чужого сайта** (блок /product/surugaya/ — японский ресейлер)

## 5. СТЕК (полный)

- Сайт: WordPress, тема Astra, Elementor, Yoast SEO, WPForms, jQuery 3.7.1
- Портал: Angular SPA (main.1dcaa0a10a89c369.js, 484 КБ), FlexProtect coreMonolith 22.118.0, Ory IdP
- API-конфиг раскрыт: `my.quomarkets.com/assets/config/overrides.json` → apiUrl `https://api.quomarkets.com`
- Трекеры: Amplitude, Intercom, Zendesk (ce5ba931-4abf-440e-996e-eaeb69e031a1), Geo Targetly (g10102301085.co)
- Почта: Microsoft 365 + Zendesk + SMTP2GO + FreshMail + Brevo + SendX

## 6. ПАРТНЁРКА (схема пирамиды)

- **/business/** — IB-программа: «proprietary trading platform», клиентский портал + бэк-офис в комплекте
- **/ambassadors/** — блогеры/компарейтеры/издатели: Apply → Connect → Earn
- Проценты — «обсуждаются индивидуально»
- В конфиге: `isCpaEnabled: false`, `isIbProfitAndPnlColumnsHidden: true`
- **naga.pl ловушка** → реферальный трекер → quomarkets (ам-track)

## 7. ЮРИДИЧЕСКАЯ СТРУКТУРА (6 офшорных юрлиц)

| Компания | Юрисдикция | «Лицензия» |
|---|---|---|
| Tradequomarkets Financial Services L.L.C | Dubai SCA | 20200000320 **Cat.5** (маркетинг, НЕ брокер) |
| Trade Quo Global Ltd | Seychelles FSA | SD140 |
| Quo Markets LLC | SVG | FSA 3171 LLC 2024 (SVG — не регулятор) |
| TQBG Ltd | Cyprus | HE438084 (регистрация, НЕ CySEC) |
| Tradequo (PTY) Ltd | ЮАР | FSP 54827 |
| TRADEQUOMARKETS LTD | Dominica | 2023/C0010-0001 (офшор) |

+ «Process Automation Ltd.» в сертификатах; LinkedIn: «QuoMarkets D Venture Markets Limited»

## 8. РЕКОМЕНДАЦИИ (следующие шаги)

1. **Проверить rabbitmq.quomarkets.com** — если консоль без пароля: полный доступ к очередям (данные депозитов/выводов!)
2. **Проверить api-auth (squid)** — открытый прокси = SSRF/абьюз
3. **system-info без авторизации** — задокументировать в жалобы
4. **Тексты жалоб**: FSA Seychelles, SCA Dubai, KNF/UOKiK Польша, FSCA ЮАР, регулятор SVG, Trustpilot, WikiFX
5. **Пакет takedown**: Cloudflare abuse, AWS (register), OVH (51.68.54.184), хостинг WP

## 8а. ПРОВЕРЕНО (2026-08-13, статус «открытый доступ?»)

| Поверхность | Проверка | Статус |
|---|---|---|
| rabbitmq.quomarkets.com `/api/overview` | GET через прокси | **401 — ЗАЩИЩЕНО** (консоль торчит, но auth есть) |
| api-auth.quomarkets.com (squid) | GET корень / CONNECT | **404 nginx / 400 CF — ЗАКРЫТО** (squid не доступен извне) |
| `/api/v2/my/system-info` | GET без токена | **200 — ОТКРЫТО (утечка!)**: tenant, вендор FlexProtect, Zendesk, APK, Amplitude-ключ |
| CORS на WP | заголовки | **МИСКОНФИГ**: `allow-origin: *` + `allow-credentials: true` |
| HSTS | заголовки | **ОТСУТСТВУЕТ** на всех хостах |
| wp-json/users | GET | 401 (REST открыт, перечисление закрыто) |

**Вердикт:** единственная подтверждённая утечка с открытым доступом — `/api/v2/my/system-info` (раскрытие внутренней инфраструктуры). RabbitMQ и squid НЕ открыты анонимно — только поверхности.

## 9. АРТЕФАКТЫ (./output)

- quomarkets_subdomains.txt (37), quomarkets_httpx.json, quomarkets_nmap*.txt
- quomarkets_main.html, quomarkets_robots.txt, quomarkets_sitemap.xml
- quomarkets_js.txt + quomarkets_js/ (3 бандла), quomarkets_endpoints.txt
- quomarkets_business.html, quomarkets_ambassadors.html, quomarkets_portal.html
- quomarkets_ovh_traefik.txt, quomarkets_aws_register.txt
