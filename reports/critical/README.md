# 🔴 КРИТИЧЕСКИЕ НАХОДКИ (эксплуатация возможна / данные под угрозой)

Дата сбора: 2026-08-13 · Источник: офис агентов + паук + разведка через прокси

---

## 1. ABET Global (abetglobal.com) — индийский скам-брокер

### Крит: Открытые CRM-админки в DNS
- **testadmin.abetglobal.com** — «Broker CRM - Admin Panel» (React/Vite, IIS/ASP.NET) — ЖИВОЙ 200
- **eedmin.abetglobal.com** — вторая копия админки (опечатка admin!) — ЖИВОЙ 200
- Непрод в проде: uat, staging, testmt5, testadmin — открыты наружу

### Крит: 250 API-эндпоинтов извлечено из бандла
- `output/abet_endpoints.txt` — полный список
- Живой логин: `POST /api/Accounts/Login` (email+password) — активен
- `GET /api/AdminManagement/*` → 401 «UnAuthorized - Token Expired» (API существует)
- Финансовые: `/Clients/ClientDeposit`, `/Clients/ClientWithdrawal`, `/Clients/GetClientWallets`, `/Clients/DepositHistory`
- Админ: `/AdminManagement/CreateUser`, `/AdminManagement/ResetPassword`, `/AdminManagement/Users`
- Рефералы: `/Affiliate/*` (механика пирамиды)

### Крит: Открытые порты + Windows-почта
- Порты: **21 (FTP), 110 (POP3), 143 (IMAP), 443, 587 (SMTP)** — открыты
- **MailEnable smtpd 10.54** — Windows-почта (исторические CVE: buffer overflow IMAP CVE-2004-2501)
- ОС: Windows, IIS/10.0, ASP.NET
- mt5api:443 OPEN — реальный MT5-трейдинг

### Крит: Схема скама подтверждена
- Нет лицензии (WikiFX: not regulated) · плечо 1:1000 (нелегально ЕС)
- Жалобы: «Missing Funds and Trade Manipulation» + SCAM ALERT
- Бонусы до 100% · домен зафиксирован · телефон UK — подделка
- «Офис в Софии» фикция: реально Индия (BookAndHost) + США (Psychz)

---

## 2. QuoMarkets (quomarkets.com) — скам-брокер

### Крит: 6 офшорных юрлиц = обман регуляцией
| Компания | Юрисдикция | Реальность |
|---|---|---|
| Tradequomarkets Financial Services L.L.C | Dubai SCA | **Cat.5 = маркетинг, НЕ брокерская лицензия** |
| Quo Markets LLC | Saint Vincent | **SVG не выдаёт форекс-лицензии** (регистрация LLC) |
| TRADEQUOMARKETS LTD | Dominica | чистый офшор |
| TQBG Ltd | Cyprus HE438084 | регистрация, НЕ CySEC |
| Trade Quo Global Ltd | Seychelles SD140 | офшор |
| Tradequo (PTY) Ltd | ЮАР FSP 54827 | реальная (местная) |

### Крит: MIMO-политика вывода (заморозка средств)
- «мы можем обработать вывод только до суммы вашего депозита на карту» — прибыль застрянет
- Жалобы WikiFX: проблемы с выводом, slippage

### Крит: Реферальная ловушка naga.pl
- naga.pl (живая, 200) → JS-редирект на quomarkets + трекер `t2954.am-track.pl/track.php?track=...&ref=<реферер>`
- Трек-код обновлён (51640a295...) — ловушка активно эксплуатируется

---

## 3. zForex (zforex.com) — скам-брокер

### Крит: Офшор-«лицензия» + бонусы-приманки
- **MISA, Saint Vincent and the Grenadines** — SVG не регулирует форекс
- **Бонусы 30% первый депозит + 20% ре-депозит** — заманивание
- «Become an IB / Partners» — реферальная механика
- Домен жив до 2027

---

## 4. Yadix (yadix.com) — скам-брокер

### Крит: Офшор + материальная приманка
- **Seychelles FSA SD021** — офшор
- **Бонус 25% + iPhone 17 Pro** за 50 лотов в 90 дней — материальная приманка
- «Best STP for EAs, Scalping, HFT» — целятся в ботоводов
- Работает с 2010, домен до 2027
