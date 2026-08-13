# 🎯 США — ЖИВЫЕ КРИПТО-ИНВЕСТ СКАМ-ПЛОЩАДКИ (2026-08-13)

**Метод:** поиск через DDG (списки MarketDueDiligence + ForteClaim, риск-скоры) → проверка живости через HTTP-мост/SOCKS → отбор оригиналов.
**Проверено:** 30 доменов из списков, 28 мертвы/парковки, **2 живых оригинала + 1 заклеймлённый CF**.

---

## ✅ ЖИВЫЕ ОРИГИНАЛЫ

### 1. Agora Idea (agora-idea.com) — «Agora», фейковая биржа
| Факт | Данные |
|---|---|
| Статус | **200**, nginx |
| IP | **156.234.7.53** (не CF, азиатский хостинг) |
| Риск-скор | **98/100** (MarketDueDiligence: fake exchange, withdrawal fees, no payouts) |
| Открыто | `/login` 200, `/trade` 200, `/deposit` 200 (кабинет и депозиты!) |
| Регистрация | `/register` 501 (POST-only) |
| Заявляет | Bitcoin, Ethereum, Ripple, blockchain, financial technology |
| Схема | Депозит → «налоги/верификация» перед выводом → деньги вязнут |

### 2. ROQCOIN (roqcoin.com) — полноценная скам-биржа
| Факт | Данные |
|---|---|
| Статус | **200**, Cloudflare |
| DNS | A: 104.21.6.167/172.67.135.10 (CF), MX: **mail.mailxnew.com** (подозрительный почтовый сервис) |
| Жалобы | ForteClaim: blocked withdrawals, suspicious crypto activity |
| Открыто | `/login` 200, `/trade` 200, `/exchange` 200 (всё работает) |
| Признаки | **«up to 10% APY interest»** на крипту (обещание дохода), **«Bonuses for inviting»** (рефералка), Bitcoin Futures, P2P |
| Бутафория | Ссылки на bscscan/etherscan/whatsonchain (видимость реальности) |
| Данные | В HTML видна логика торгов (userOrders, ratings) — фейковая витрина |

## ⚠️ ЗАКЛЕЙМЛЁН (живой, но заблокирован)

### 3. AGCCoin (agccoin.com)
- **403 «Suspected Phishing | Cloudflare»** — Cloudflare сам заблокировал как фишинг
- Жалобы: pig butchering scam (ForteClaim)
- Вывод: домен жив, но CF режет трафик — подтверждение скама от CDN

## ❌ МЁРТВЫЕ / ПАРКОВКИ (проверено, отсеяны)

| Домен | Статус | Причина |
|---|---|---|
| zipmexpro.com | 200 | **Парковка above.com** (park-mx), не проект |
| quaxs.com | 302 | **Домен на продаже** (hugedomains) |
| bitmainoptiontrade.com | 000 | Мёртв |
| bondltdfinance.com | 000 | Мёртв |
| cryptocoinxchange.com | 000 | Мёртв |
| clfcoin.com | 000 | Мёртв |
| cryptomms.com | 000 | Мёртв |
| cryptts.cc | 000 | Мёртв |
| btecgcrypto.vip | 000 | Мёртв |
| doublexrp.org | 405/000 | Мёртв |
| coinget.finance | 501 | Полуживой |
| quantumxex.net, bitboxn.com, fandc.ai, stilwellinvestings.com, globaltraderalliance.com, bhpvipai.com, vekbit.com, defiwa11etbch.com, defie-v2.com, ldgbite.com | 000/405 | Мёртвы |

## 🧬 Общая схема (US-криптоскам 2026)
```
Фейковая биржа (витрина с реальными тикерами/APY/рефералками)
→ жертва через WhatsApp/Telegram/соцсети (pig butchering)
→ депозит крипты (BTC/ETH/USDT)
→ фейковые профиты на дашборде
→ вывод заблокирован → «налоги/верификация/комиссии»
→ деньги уходят в кошельки скамеров (необратимо)
```

## 📋 Дальнейшие шаги (по приказу)
- [ ] Глубокая разведка agora-idea.com (поддомены, JS, порты 156.234.7.53)
- [ ] Глубокая разведка roqcoin.com (поддомены, API, JS-бандлы)
- [ ] Поиск ещё живых: списки Watchlist MDD, DFPI CA crypto scam tracker, FTC
- [ ] Пакет takedown: Cloudflare abuse (roqcoin), хостинг agora, IC3/FTC/DFPI

## 📂 АРТЕФАКТЫ
- output/usa_scam_projects.txt (список проверенных доменов)
- Источники: marketduediligence.com/newly-reported-crypto-scam-platforms-2026, forteclaim.com/top-50-crypto-scams-of-2026
