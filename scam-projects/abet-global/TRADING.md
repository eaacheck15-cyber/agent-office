# 📈 TRADING.MD — Торговый профиль скама: ABET Global (abetglobal.com)

**Тип:** форекс-пирамида / скам-брокер · **Статус:** активный · **Дата:** 2026-08-13
**Основа:** разведка через SOCKS5-ротатор, swagger-документы, JS-бандлы, nmap. Без эксплуатации.

---

## 🖥 MT5 / ТОРГОВАЯ ИНФРАСТРУКТУРА (реальная)

| Компонент | Хост | Статус | Детали |
|---|---|---|---|
| MT5-сервер | `mt5api.abetglobal.com` | 443 OPEN | Реальный MetaTrader-трейдинг (порт 443 открыт) |
| MT5-тест | `testmt5.abetglobal.com` | 404 (HTTPAPI) | Тестовый контур |
| MetaAPI | `metaapi.abetglobal.com` | 404 | Интеграция MetaApi (облачный MT5) |
| Крипто-тест | `cryptotest.abetglobal.com` | 404 | Тест крипто-депозитов |

**Модель `Platforms` (из открытого Swagger, applicationapi):**
```
platformId, platform, serverIP, serverPort,
serverLoginID, serverPassword,        ← логин/пароль боевого MT5-сервера
demoServerIP, demoServerPort, demoLoginID, demoServerPassword,  ← демо
contestServerIP, contestServerPort, contestLoginID, contestServerPassword ← конкурсы
```

→ Вся MT5-инфраструктура описана в API-моделях: **пароли MT5-серверов хранятся в БД** (таблица Platforms).

## 💰 СЧЕТА, ПЛЕЧО, УСЛОВИЯ (данные из API-моделей)

### Типы счетов (`AccountTypes` из swagger)
```
accountTypeId, accountType, accountGroupType, accountGroup,
isAccountLimitRequired, minAccountLimit, isActive, isDeleted,
accountLeverages (связь с плечами), userAccounts
```

### Плечи (`Leverages`, `AccountLeverages`)
```
leverageId, leverage, isActive, isDeleted, accountLeverages, userAccounts
```

### Маркетинговые условия (с главного сайта / разведки)
| Параметр | Значение | Комментарий |
|---|---|---|
| Максимальное плечо | **1:1000** | В ЕС лимит ESMA — 1:30. Нарушение. |
| Бонус на депозит | **до 100%** | Классическая приманка скам-брокеров |
| Trading credit | **30%** | «Кредит», который нельзя вывести |
| Мин. депозит | **$10** | Порог вовлечения жертв |
| Продукты | Forex, Crypto, Metals, Indices, Energies | Заявляет «Best Regulated» на лендингах |

## 💸 ДЕПОЗИТЫ / ВЫВОДЫ (финансовый контур)

### Модель `UserFunds` (движение денег жертв)
```
userFundId, paymentReferenceId, userId, walletCategoryId, walletId,
userAccountId, amount, bonusAmount, status, fundType, description,
fundProof, withdrawalDetails, currencyRate
```

### Эндпоинты финансовых операций (CRM, за JWT)
- `/api/Clients/ClientDeposit` — приём депозитов
- `/api/Clients/ClientWithdrawal` — вывод (по жалобам WikiFX — не выплачивают)
- `/api/Clients/TransferFunds` — переводы между счетами
- `/api/Clients/ClientCreditIn` / `ClientCreditOut` — «кредиты»
- `/api/Clients/DepositHistory`, `GetClientWalletTransactions`

### Крипто-платёжки (из Swagger crypto)
- `POST /Payment/CryptoDepositResponse` — вебхук крипто-депозита
- `POST /Payment/BitNBoxDepositResponse` — **BitNBox** (криптоплатёжка)
- Модель `CryptoPaymentResponseDTO`: depositAddress, conversionRate, processingFee, finalAmount

→ Жертвы платят криптой (BitNBox) — **возврат средств невозможен** (крипта необратима).

## 🕸 ПАРТНЁРКА / РЕФЕРАЛЫ (схема привлечения)

### Модели
- `AffiliateWallet` — walletBalance (партнёрские кошельки)
- `AffiliateRequests` — userId, lastCompanyName, totalClients, totalTradingExp, status, refferLink, loginId

### Эндпоинты (CRM)
- `/api/Affiliate/GetAffiliate`, `CreateAffiliateReward`, `CreateAffiliateRewardTier`
- `/api/Affiliate/GetAffiliateFundsList`, `RejectAffiliateFund`, `ApprovedAffiliateFund`
- Loyalty: `CreateAffiliateLoyaltyEvent/Tier`, `GetAffiliateLoyaltyTiers`

### Реферальная механика на портале
- Регистрация: `manage.abetglobal.com/account/register` — поле **`refLink`** (реферальная ссылка)
- Партнёрка-лендинг: `affiliate.abetglobal.com` (в DNS)

→ Пирамида: партнёрские кошельки + реферальные ссылки + лояльность = классическая MLM-схема поверх форекс-фейка.

## 🌍 ГЕОГРАФИЯ ЖЕРТВ (косвенно)

- API справочник: `manage.abetglobal.com/generic/GetCountries` — **239 стран** (открыто, без авторизации)
- Регистрация открыта, GA-код **G-E1GLTK5PRC** — реальный трафик
- Телефоны: болгарский +359, британский +44 (фейковые реквизиты)

## ⚖ ТОРГОВЫЕ ПРИЗНАКИ СКАМА (юридически значимые)

1. **Плечо 1:1000** — прямое нарушение ESMA-лимита 1:30 для розничных клиентов ЕС
2. **Нет лицензии** (WikiFX: not regulated) при приёме розничных средств
3. **«Бонусы» и «trading credit»** — манипулятивные схемы удержания депозитов
4. **Жалобы WikiFX**: «Missing Funds and Trade Manipulation», SCAM ALERT
5. **Крипто-платежи BitNBox** — необратимость, невозможность возврата
6. **MT5-серверы с паролями в БД** (модель Platforms) — инфраструктура «под ключ», типично для купленных брокерских решений (белый лейбл)

## 📂 Артефакты по торговому контуру

- `output/applicationapi_swagger.json` — модели Platforms, UserFunds, AccountTypes, Leverages, Currencies
- `output/crypto_swagger.json` — платёжные вебхуки (BitNBox)
- `output/abet_endpoints*.txt` — финансовые эндпоинты (ClientDeposit/Withdrawal/TransferFunds)
- `output/abet_recon_report.md` — полный отчёт разведки
- `output/abet_takedown_package.md` — пакет жалоб (FSC/FCA/WikiFX/CERT-In)
