# 🎯 СКАМ-ПРОЕКТ: ПОЛЬША — рабочие скам-схемы с живым трафиком

**Дата сбора:** 2026-08-13 · **Метод:** Serper (Google, gl=pl) через прокси + проверка живости

---

## 🚨 НАЙДЕНО (рабочие, проверено)

### 1. QuoMarkets Global (quomarkets.com) — АКТИВНЫЙ скам-брокер
| Факт | Данные |
|---|---|
| Сайт | https://www.quomarkets.com (www: **200**, 299 КБ, живой) |
| Заявленные лицензии | Seychelles FSA + Cyprus Reg. No. HE438084 (офшорный набор) |
| IP | за Cloudflare (2606:4700...) |
| Домен | создан 2022-10-25, жив до 2033 |
| Признаки | «No Commission», ASIC упоминание (маркетинг), офшорные лицензии |
| Партнёрка | есть раздел Partners/affiliates («affiliates do not target EU» — обход регуляции) |
| **Ловушка входа** | **naga.pl редиректит на quomarkets + реферальный трекер** |

### 2. naga.pl — РЕФЕРАЛЬНАЯ ЛОВУШКА (живая, 200)
- НЕ брокер! Это редирект-страница (299 б) с JS:
  - `meta refresh 5s → quomarkets.com`
  - JS: `t2954.am-track.pl/track.php?track=ec6df0100ed5a2c4c59b9c8a56751747&ref=document.referrer`
- **Смысл**: партнёрский трекер — за каждого завлечённого через реферер идёт комиссия
- Трекер am-track.pl сейчас истёк (302 → aftermarket.pl, домен на продаже), но **сайт всё ещё редиректит на него**
- Домен-приманка «naga» (созвучно крупному бренду) — типичная схема клонирования имён

### 3. FxGrow (fxgrow.pl → fxgrow.com) — живой
- fxgrow.pl: 301 → fxgrow.com (международный, домен 2009, жив до 2031)
- Прямой доступ с нашего IP блокирован, через прокси 301 — проверить глубже

### 4. Purple Trading (purple-trading.pl) — живой, 200
- Польский форекс-брокер, работает (нужна проверка на скам-признаки)

---

## 🧬 Механика схемы (выявлена)

```
Приманка (naga.pl / бонус-сайты / реклама)
    ↓  (редирект + трекер ref=)
QuoMarkets / FxGrow (офшорные лицензии)
    ↓
Жертва вносит депозит (мин $10, бонусы до 100%)
    ↓
Вывод блокируется / «нужна верификация» / деньги пропадают
```

## 📋 Дальнейшие шаги (по приказу)

- [ ] Глубокая проверка QuoMarkets: 250+ страниц, реальные лицензии, жалобы WikiFX/Trustpilot
- [ ] Проверить партнёрскую программу QuoMarkets (механика пирамиды)
- [ ] Проверить FxGrow и Purple Trading на скам-признаки
- [ ] Собрать доказательства + тексты жалоб (KNF Польши, UOKiK, офшорные регуляторы)

---

## 🔍 QuoMarkets — ГЛУБОКИЙ РАЗБОР (2026-08-13)

### Юридическая структура (лавина офшорных компаний)
| Компания | Юрисдикция | Лицензия |
|---|---|---|
| Tradequomarkets Financial Services L.L.C | **Dubai, UAE** (SCA) | 20200000320 Cat.5 (только «консультации и интродукция» — НЕ брокерская!) |
| Trade Quo Global Ltd | **Seychelles FSA** | SD140 |
| Quo Markets LLC | **Saint Vincent (SVG)** | FSA 3171 LLC 2024 (SVG — не регулятор! просто регистрация) |
| TQBG Ltd | **Cyprus** | HE438084 (зарегистрирован, НЕ лицензирован CySEC) |
| Tradequo (PTY) Ltd | **ЮАР** | FSP 54827 |
| TRADEQUOMARKETS LTD | **Dominica** | 2023/C0010-0001 (офшор без регуляции) |

### Ключевые красные флаги
1. **Dubai-лицензия SCA Cat.5** — «Financial Consultations and Introduction» — это НЕ лицензия брокера, а разрешение на маркетинг! Клиенты думают, что брокер «регулируемый», а он просто привлекает клиентов.
2. **Saint Vincent (SVG) FSA 3171 LLC** — SVG вообще не выдаёт лицензий на форекс, это регистрация LLC. «FSA 3171 LLC 2024» — просто регистрационный номер компании.
3. **Cyprus HE438084** — регистрационный номер компании, не CySEC-лицензия (маскировка под «кипрскую регулируемую»).
4. **Dominica TRADEQUOMARKETS LTD** — офшор, нет реальной регуляции.
5. **Trustpilot 5.0/4K отзывов** — «We don't fact-check reviews» — сомнительно (могут быть накручены).
6. **WikiFX core score 7.27** — но есть exposure-отчёты о проблемах с выводом (slippage, задержки).
7. **BrokerChooser: «not safe, not regulated by authority with strict rules»**.
8. **naga.pl ловушка** — реферальный трафик на QuoMarkets (привлечение через трекер).

### Механика
```
Дубайская «лицензия» SCA Cat.5 (маркетинг) + SVG/Dominica (офшор)
→ реклама «regulated broker» + naga.pl реферальный трафик
→ жертвы вносят депозит ($10+, «no commission», бонусы)
→ вывод: «MIMO policy — только до суммы депозита», жалобы на slippage/задержки
```

### Доказательства (ссылки)
- WikiFX: https://www.wikifx.com/en/dealer/2737536119.html
- BrokerChooser: https://brokerchooser.com/safety/httpsquomarketscom-broker-safe-or-scam
- Trustpilot: https://www.trustpilot.com/review/www.quomarkets.com
- Myfxbook: https://www.myfxbook.com/reviews/brokers/quomarkets/3163748,1

---

## ✅ ЖИВЫЕ СКАМ-ПЛОЩАДКИ (проверено 2026-08-13, через прокси)

### 1. zForex (zforex.com) — ЖИВОЙ (200)
| Факт | Данные |
|---|---|
| Сайт | https://zforex.com (200, 80 КБ) |
| «Лицензия» | **MISA, Saint Vincent and the Grenadines** (SVG — НЕ форекс-регулятор, регистрация LLC) |
| Бонусы | **30% первый депозит, 20% ре-депозит** (приманки) |
| Партнёрка | «Become an IB / zForex Partners» |
| Домен | 2006-06-16, жив до 2027-06-16 |

### 2. QuoMarkets (quomarkets.com) — ЖИВОЙ (200)
(см. раздел выше: 6 офшорных компаний, Dubai SCA Cat.5 маркетинговая, SVG 3171 LLC, Dominica, Cyprus не-CySEC, MIMO-вывод)

### 3. naga.pl — ЖИВАЯ РЕФЕРАЛЬНАЯ ЛОВУШКА (200)
- Редирект на quomarkets + трекер am-track (track-код **обновлён**: 51640a295a5b5d5ad0f2ce3df1cc2132)
- Ловушка активно эксплуатируется (код меняется = трафик идёт)

### 4. purple-trading.pl — живой (301 → purple-trading.com/pl) — легальный брокер (проверен)

### Отсеяны (не скам-площадки, живые но не подходят)
- forexrev.com — обзорник брокеров (Reviews & Scam Alerts)
- offbeatforex.com, tradingpedia.com, fxrecap.com, trading.com — обзорники/агрегаторы бонусов
- test4profit.pl — блог трейдера
- fxgrow.pl → fxgrow.com — международный брокер (домен 2009)

## 📋 ИТОГ: рабочие скам-элементы в зоне Польши
| Площадка | Статус | Роль |
|---|---|---|
| zForex (zforex.com) | ЖИВОЙ | офшор-брокер SVG, бонусы 30% |
| QuoMarkets (quomarkets.com) | ЖИВОЙ | офшор-брокер, 6 юрлиц, MIMO-вывод |
| naga.pl | ЖИВОЙ | реферальная ловушка → QuoMarkets |
