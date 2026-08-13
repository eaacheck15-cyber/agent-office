# 🤖 Agent Office

Единый «офис» всех агентов для opencode. Все агенты собраны в одном проекте из GitHub-поиска.

## Состав (142 агента)

| Источник | Репозиторий | Кол-во |
|---|---|---|
| Core-субагенты (dev, infra, data, QA, бизнес, оркестрация, research) | [ankitmundada/awesome-opencode-subagents](https://github.com/ankitmundada/awesome-opencode-subagents) | 128 |
| Оркестратор + субагенты закрытого цикла (solo/editor/reviewer/verify/observer/explore/general) | [Dqz00116/opencode-solo](https://github.com/Dqz00116/opencode-solo) | 7 |
| PM-ops команда (PM, QA, GTM, data-analyst, UX, support, research) | [bahni-m/minions](https://github.com/bahni-m/minions) | 7 |

## Структура

```
office/
├── opencode.jsonc          # конфиг офиса: оркестратор + venice + vision + cloner
├── README.md
└── .opencode/
    ├── agent/              # 142 файла субагентов (name.md)
    └── skills/
        └── minions/SKILL.md
```

## Ключевые агенты

- **orchestrator** — главный. Полностью автономен, маршрутизирует задачи между агентами (deepseek-v4-flash)
- **venice** (Винсент) — аблатерированный кодер, gemma-4-uncensored, tool calling
- **vision** — анализ изображений/скриншотов/OCR (gpt-5-nano)
- **cloner** — точное клонирование сайтов (deepseek-v4-flash)
- **solo-solo** — primary-оркестратор закрытого цикла (тесты→правки)

## Установка

```bash
# конфиг уже в проекте — откройте opencode в этой папке:
cd office && opencode
```

Агенты подхватываются автоматически из `.opencode/agent/` (142 субагента) + `opencode.jsonc` (базовые).

## Примечания

- Файлы из awesome-opencode-subagents сконвертированы: `tools:` → `permission:` (валидный формат opencode)
- У minions-агентов модель заменена на `deepseek/deepseek-v4-flash` (провайдер из коробки)
- Источники: поиск GitHub по `opencode agent`, `opencode subagents`, `opencode skills`
