# ABET Global — Пакет легального takedown (2026-08-13)

Скам-брокер: abetglobal.com. Подготовлено на основе разведки (доказательная база ниже).
Отправлять по каналам в порядке приоритета. Тексты готовы к вставке.

---

## 0. Доказательная база (краткая сводка для жалоб)

| Факт | Доказательство |
|---|---|
| Мошеннический форекс-брокер без лицензии | WikiFX: «not regulated», SCAM ALERT, жалобы «Missing Funds and Trade Manipulation» |
| Ложные юрисдикции | Заявляет Софию (Болгария), фактически сервер в США (Psychz, Даллас), rDNS → индийский BookAndHost |
| Нарушение правил торговли | Плечо 1:1000 (в ЕС лимит 1:30), бонусы-приманки до 100% |
| Инфраструктура | IP 108.181.154.20 (AS40676 Psychz), Windows, IIS 10.0, MailEnable 10.54, FileZilla 0.9.60 beta |
| Признаки нелегальной деятельности | Публичная регистрация админом форума (role=Admin), пароли по HTTP без редиректа, невалидные TLS-сертификаты |
| Реальные жертвы | Google Analytics G-E1GLTK5PRC (живой трафик), регистрация открыта |
| Фейковые контакты | Тел. +359 2 492 8517 (BG), +44 7548 718055 (UK), адрес «34 Ralevista street, Sofia» |

---

## 1. Abuse хостингу Psychz Networks (ПРИОРИТЕТ №1 — бан сервера убьёт сайт)

**Кому:** abuse@psychz.net (также noc@psychz.net)
**Тема:** Fraudulent forex broker (scam) hosted on your network — IP 108.181.154.20

```
Dear Psychz Networks Abuse Team,

We are reporting IP address 108.181.154.20 (AS40676) hosting a fraudulent
"forex broker" website: abetglobal.com.

Facts:
- The site claims to be a regulated Bulgarian broker (office in Sofia) but is
  in fact an unregulated scam. Complaints are registered on WikiFX (SCAM
  ALERT, "Missing Funds and Trade Manipulation", July 2026).
- It offers illegal leverage up to 1:1000 and bonus schemes designed to
  defraud retail clients (minimum deposit $10).
- The server hosts two live broker-CRM admin panels (testadmin.abetglobal.com,
  eedmin.abetglobal.com) and a client portal (manage.abetglobal.com) used to
  take deposits from victims.
- No financial license exists in Bulgaria (FSC) or any EU jurisdiction.
- DNS reverse record points to mail.bookandhost.in (Indian reseller).

This is a clear violation of your Acceptable Use Policy (fraudulent activity).
We request immediate suspension of this server.

Supporting details: IP 108.181.154.20, ports 21/110/143/443/587 open,
MailEnable 10.54, FileZilla 0.9.60 beta, IIS 10.0.

Thank you.
```

## 2. Abuse BookAndHost (индийский провайдер, rDNS mail.bookandhost.in)

**Кому:** support@bookandhost.com (найти актуальный abuse-адрес на сайте)
**Тема:** Your customer hosts a fraudulent forex broker (abetglobal.com)

```
Dear BookAndHost,

Your infrastructure (rDNS mail.bookandhost.in / mail.bookandhost.com) is
linked to IP 108.181.154.20, which hosts abetglobal.com — a fraudulent
unregulated "forex broker" that collects money from victims under false
pretenses (fake Bulgarian office, complaints on WikiFX, no license).

As an Indian hosting provider you are legally exposed. We request you
terminate this customer and cooperate with authorities.
```

## 3. Регистратор PublicDomainRegistry (PDR Ltd) — деактивация домена

**Кому:** abuse@publicdomainregistry.com
**Тема:** Fraudulent domain abetglobal.com — take down request

```
Dear PDR Ltd,

Domain: abetglobal.com (registered 2022-07-15, status clientTransferProhibited).

This domain operates a fraudulent forex broker scam (no license, fake
Bulgarian office, victim complaints on WikiFX, illegal leverage 1:1000).
Such use violates ICANN abuse policies and your Acceptable Use Policy.

Requesting domain suspension/lock and cooperation with law enforcement.
Registrant contact data is falsified (fake UK/BG phone numbers).
```

## 4. Google (Safe Browsing + Ads) — чёрная метка «обман»

- **Safe Browsing:** https://safebrowsing.google.com/safebrowsing/report_phish/ (указать abetglobal.com, класс «мошенничество»)
- **Google Ads:** жалоба через Google Ads Help на рекламу брокера; также подать в Google Transparency Report.
- Аналитика: трафик меряется через G-E1GLTK5PRC — упомянуть в жалобе.

## 5. Meta (Facebook) — бан фейковой страницы

- Страница: facebook.com/abetglobal
- Канал: https://www.facebook.com/help/contact/169486816475734 (мошенничество/обман)
- Текст: «ABET Global (abetglobal.com) is an unregulated scam broker collecting
  deposits from victims under false Bulgarian identity. Please remove the page.»

## 6. FSC Болгария (заявляет юрисдикцию Софии)

- Сайт: fsc.bg (Financial Supervision Commission)
- Текст: жалоба на «ABET Global» — работа с розничными клиентами без лицензии,
  ложный офис в Софии (34 Ralevista street), плечо 1:1000 (нарушение ESMA 1:30).

## 7. FCA UK (фейковый британский номер +44 7548 718055)

- Канал: https://www.fca.org.uk/consumers/report-scam-unauthorised-firm
- Указать: компания использует UK-номер без FCA-авторизации (clone/unauthorised firm).

## 8. WikiFX (обновить/подтвердить жалобы)

- Уже есть: SCAM ALERT, «Missing Funds and Trade Manipulation».
- Добавить новые данные: живые админки, регистрация админом форума, утечка путей.

## 9. Индия: CERT-In и cybercrime.gov.in (фактический хостинг — Индия)

- https://cybercrime.gov.in — подать жалобу (мошенничество с использованием
  индийского хостинга BookAndHost).
- cert-in.org.in — уведомить о фишинговом/мошенническом ресурсе.

---

## 10. Ожидаемый эффект

1. **Psychz / BookAndHost** → бан сервера → сайт, админки и портал падают (всё на одном IP).
2. **PDR** → деактивация домена → DNS умирает.
3. **Google / Meta** → чёрные метки → трафик жертв прекращается.
4. **FSC / FCA / WikiFX / CERT-In** → официальные блокировки и уголовная линия.

Порядок отправки: 1 → 2 → 3 (в тот же день), затем 4-9 в течение недели.
Дублируйте жалобы с разных email. Сохраняйте номера обращений.
