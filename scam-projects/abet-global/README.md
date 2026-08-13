# 🎯 СКАМ-ПРОЕКТ: ABET Global (abetglobal.com)

**Статус:** активный · **Тип:** форекс-пирамида / скам-брокер · **Юрисдикция:** Индия+США (под видом Болгарии)

---

## 📍 ДОСТУП (проверено, живой)

| Ресурс | URL | Статус |
|---|---|---|
| Главный сайт | https://abetglobal.com | **200** (живой) |
| Регистрация | https://abetglobal.com/sign-up | 200 (SPA) |
| **CRM-админка 1** | https://testadmin.abetglobal.com | **200** |
| **CRM-админка 2** | https://eedmin.abetglobal.com | **200** |
| Портал клиентов | https://manage.abetglobal.com | **200** |
| Кабинет | https://secure.abetglobal.com | 200 |
| Форум | https://forum.abetglobal.com | 302→/Account/Login |

## 🛠 СТЕК (выявлен)

- ОС: **Windows** (nmap), IIS 10.0, ASP.NET (X-Powered-By)
- Почта: **MailEnable 10.54** (SMTP 587, POP3 110, IMAP 143)
- Frontend админки: React/Vite (бандл 1.9 МБ), SignalR, Axios, Quill
- Админка 2 (`eedmin`) — отдельный бандл (index-K8NvZeNx.js)
- Сертификат: Let's Encrypt (CN=testadmin.abetglobal.com)
- Прокси-метки: banner иногда «IPG8000» (WAF/прокси-слой)

## 🧬 ПОВЕРХНОСТЬ АТАКИ (подтверждено)

- Порт 21 (FTP), 110 (POP3), 143 (IMAP), 443 (HTTPS), 587 (SMTP) — открыты
- 20 поддоменов: api, manage, secure, crypto, forum, staging, testadmin, eedmin,
  uat, testmt5, mt5api (MT5-сервер, 443 OPEN), metaapi, affiliate, mail, cryptotest...
- **250 API-эндпоинтов** (output/abet_endpoints.txt):
  - `/api/Accounts/Login` (email+password, активен)
  - `/api/AdminManagement/*` → 401 (Users, Roles, CreateUser, ResetPassword)
  - `/Clients/*` → ClientList, GetClientWallets, ClientDeposit, ClientWithdrawal
  - `/Affiliate/*` → реферальная механика
- Auth: JWT в localStorage/sessionStorage («token»), XSRF-token
- 2 админки с разными бандлами = минимум 2 контура

## 🕳 УЯЗВИМОСТИ (что найдено, без эксплуатации)

1. **Открытые админки в DNS** — testadmin/eedmin/uat/staging/testmt5 торчат наружу
2. **MailEnable 10.54** — Windows-почта на борту (исторические CVE: buffer overflow IMAP CVE-2004-2501 и др.)
3. **Отсутствуют security-заголовки** (nikto): нет CSP, HSTS, X-Content-Type-Options, Referrer-Policy
4. **BREACH-кандидат**: Content-Encoding: deflate
5. **TRACE разрешён** (nikto: OPTIONS, TRACE, GET, HEAD, POST)
6. **Клиентский кабинет + API** на одном сервере — нет сегментации
7. **SPF слабый**: `~all` (softfail) + include:outbound.mailhop.org

## 🚫 ЧТО НЕ ДЕЛАЕМ

- Не проводим подбор паролей / эксплуатацию без авторизации (это взлом, не разведка)
- Не атакуем живую CRM (там деньги жертв)
- Все проверки — только открытые данные + пассивный/полуактивный анализ через прокси

## ✅ ЛЕГАЛЬНЫЕ ДЕЙСТВИЯ (следующие шаги)

1. Собрать доказательную базу (DNS, whois, скриншоты, nikto-вывод) — для жалоб
2. Подать жалобы: FSC Болгарии, хостинг-провайдер BookAndHost, Psychz Networks, регистратор PDR
3. WikiFX — добавить данные в разоблачение
4. Анализ бандлов на захардкоженные ключи (полный дамп строк)


## 📋 ДОКАЗАТЕЛЬСТВА (собрано)

### TLS-аудит (все поддомены)
- Все: TLSv1.3, шифр TLS_AES_256_GCM_SHA384, сертификаты Let's Encrypt
- Issuer YR2 для всех, кроме `api` (YR1) — api на отдельном сертификате/контуре
- Имена в CN совпадают с хостами (валидные серты — легитимный Let's Encrypt)

### Email-инфраструктура
- Email-адреса из бандла: `admin@abetglobal.com` (рабочий), `admin@broker.com` (шаблонный)
- MX: mail.abetglobal.com → тот же сервер 108.181.154.20 (Windows MailEnable)
- SPF: `ip4:108.181.154.20 include:outbound.mailhop.org ~all` → mailhop (AWS-диапазоны 52.x/54.x) может слать почту от их имени
- SMTP 587 + POP3 110 + IMAP 143 открыты — полноценная почтовая инфраструктура для рассылок жертвам

### Гео (подтверждено)
- IP 108.181.154.20: США, Техас, Даллас (Psychz Networks AS40676)
- Провайдер хостинга: BookAndHost (Индия, +91)

### Строки бандла (чистые)
- HTTP-URLs: 0 (все API-вызовы относительные — идут на тот же origin)
- API-пути: 241 уникальных (250 с мелкими)
- base64: ложные срабатывания (эндпоинты), реальных ключей нет
- hex-ключи: 0
- Реальные email: admin@abetglobal.com

## 📂 АРТЕФАКТЫ

- `targets/abet-global.md` — полный разведотчёт
- `output/abet_endpoints.txt` — 250 эндпоинтов
- `output/abet_admin.js` — бандл админки 1
- `output/abet_nmap.txt` — скан портов
- `output/nikto_admin_v5.txt` — nikto-скан админки
