# 🤖 Agent Office

Единый «офис» всех агентов для opencode. Все агенты собраны в одном проекте из GitHub-поиска.

## 🎯 Активная цель (вводные для агентов)

> **[удалено]

## Состав (230 агентов)

| Источник | Репозиторий | Кол-во |
|---|---|---|
| Core-субагенты (dev, infra, data, QA, бизнес, оркестрация, research) | [ankitmundada/awesome-opencode-subagents](https://github.com/ankitmundada/awesome-opencode-subagents) | 128 |
| Оркестратор + субагенты закрытого цикла (solo/editor/reviewer/verify/observer/explore/general) | [Dqz00116/opencode-solo](https://github.com/Dqz00116/opencode-solo) | 7 |
| PM-ops команда (PM, QA, GTM, data-analyst, UX, support, research) | [bahni-m/minions](https://github.com/bahni-m/minions) | 7 |
| **Пентест: kill-chain + специализация** (recon, AD, API, web, cloud, mobile, IoT, wireless, crypto, exploit, privesc, post-ex, C2, evasion, malware, DFIR, blue-team, отчёты) | [mukul975/Threatswarm](https://github.com/mukul975/Threatswarm) | 27 |
| **Пентест: 53 роли** (recon, web-hunter, api-security, exploit-chainer, payload-crafter, privesc, lateral-movement, c2-operator, osint, phishing, malware, reverse, DFIR, bug-bounty, CTF, отчёты) | [0xSteph/pentest-ai-agents](https://github.com/0xSteph/pentest-ai-agents) | 53 |
| **Пентест: автономный оркестратор + разведка** (loki, odin, recon, vuln-scanner, exploit) | [Lolicks/loki-pentest-agent](https://github.com/Lolicks/loki-pentest-agent) | 5 |
| Пентест: recommend + scope-guard | [humaidhahm/opencode-pentester](https://github.com/humaidhahm/opencode-pentester) | 2 |

## Структура

```
office/
├── opencode.jsonc          # конфиг офиса: оркестратор + venice + vision + cloner
├── README.md
├── publish.sh              # публикация на GitHub
├── container/              # закрытый контейнер с SOCKS5-пулом
└── .opencode/
    ├── agent/              # 230 файлов субагентов (name.md)
    └── skills/             # minions, loki-pentest, opencode-pentester
```

## Ключевые агенты

- **orchestrator** — главный. Полностью автономен, маршрутизирует задачи между агентами (deepseek-v4-flash)
- **venice** (Винсент) — аблатерированный кодер, gemma-4-uncensored, tool calling
- **vision** — анализ изображений/скриншотов/OCR (gpt-5-nano)
- **cloner** — точное клонирование сайтов (deepseek-v4-flash)
- **loki-loki** — автономный пентест-оркестратор (сканы параллельно, цепочки эксплойтов)
- **ts-***, **pentai-*** — 80 пентест-ролей полного kill-chain

## Установка

```bash
# конфиг уже в проекте — откройте opencode в этой папке:
cd office && opencode
```

Агенты подхватываются автоматически из `.opencode/agent/` (230 субагентов) + `opencode.jsonc` (базовые).

## Пентест-агенты (88)

Все пентест-агенты: авторизованный тест только, чек scope перед атакой.
- `ts-*` — 27 агентов Threatswarm (полный kill-chain: recon → exploit → post-ex → отчёт)
- `pentai-*` — 53 агента pentest-ai-agents (роли от recon до swarm-orchestrator)
- `loki-*` — 5 агентов автономного пентеста
- `op-*` — recommend (маршрутизация задач к нужному пентестеру) + scope-guard

## Закрытый контейнер с SOCKS5-пулом

`container/` — изолированный Docker-контейнер, весь сетевой выход наружу только через SOCKS5-прокси из пула.

- Пул добывается из GitHub-списков + API (proxyscrape) и пересобирается каждые 600 с — всегда свежие
- Ротация: на каждый запрос берётся следующий живой прокси из пула (round-robin)
- Внутри контейнера нет прямого доступа в интернет — только через пул

```bash
cd office/container && docker build -t agent-office-proxy . && ./run.sh
```

## Примечания

- Файлы сконвертированы в валидный opencode frontmatter (`tools:` → `permission:`, модели → `deepseek/deepseek-v4-flash`)
- Источники: поиск GitHub по `opencode agent`, `opencode subagents`, `opencode skills`, `pentest agent`, `pentesting skills`
