# Oncology Research Assistant — решение хакатона «Цифровое здоровье»

Команда **hakatonleo3** · трек 3 — AI-ассистент для научных исследований.

## Что это

Мультиагентная LLM-система для доказательного анализа литературы по PubMed: врач-онколог задаёт клинический вопрос на естественном языке, ассистент проводит структурированный поиск, оценивает качество источников по принятым в EBM методикам и формирует итоговый отчёт со ссылками на конкретные PMID.

## Пайплайн (6 агентов)

1. **Verifier** — структурирует вопрос в PICO + 3 поисковых запроса
2. **Researcher** — ищет в PubMed через E-utilities API
3. **Scoping** — обзор научного поля (Scoping Review)
4. **Critic** — оценка качества по RoB 2.0 / ROBINS-I / STROBE / Oxford CEBM
5. **Meta-Checker** — оценка возможности метаанализа (Cochrane Handbook)
6. **Synthesizer** — финальный аналитический отчёт в Markdown

Стек: Python 3.11 · Yandex AI Studio (LLM) · PubMed E-utilities · Streamlit · Docker.

## Покрытие критериев хакатона

| № | Категория | Реализация |
|---|---|---|
| 1 | Функциональность пайплайна | Полный путь вопрос → отчёт, 6 агентов |
| 2 | Поиск и проверяемость | Реальные PMID/DOI из PubMed, 3 параллельных запроса |
| 3 | Scoping review | Отдельный агент: типы публикаций, популяции, пробелы |
| 4 | Систематический обзор | PICO + критерии включения + таблица + PRISMA-диаграмма |
| 5 | Метаанализ | Чекер по Cochrane Handbook (без расчёта forest plot) |
| 6 | Критическая оценка | RoB 2.0, ROBINS-I, STROBE, AMSTAR-2, Oxford CEBM 1–5 |
| 7 | Качество LLM-ответа | Опора только на абстракты, явные дисклеймеры |
| 8 | UX/UI | Веб-приложение на Streamlit |
| 9 | Код и воспроизводимость | Docker, README, DEPLOY, docs/, фикс. версии |

## Быстрый запуск

### Docker (рекомендуется)

    git clone <repo_url>
    cd hakatonleo3
    cp .env.example .env  # заполните YANDEX_API_KEY и YANDEX_FOLDER_ID
    docker compose up --build

Веб-интерфейс откроется на http://localhost:8501

### Локально

    python3.11 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    streamlit run src/web/app.py

Подробности — [DEPLOY.md](DEPLOY.md).

## Документация

- [docs/overview.md](docs/overview.md) — проблема, цель, сценарии использования
- [docs/architecture.md](docs/architecture.md) — архитектура агентов, поток данных
- [docs/data_schema.md](docs/data_schema.md) — схемы PICO, Critique, Meta-Check
- [ETHICS.md](ETHICS.md) — этические принципы, ограничения

## Структура репозитория

    .
    ├── README.md                          # этот файл
    ├── DEPLOY.md                          # инструкции по развёртыванию
    ├── Dockerfile, docker-compose.yml     # контейнеризация
    ├── requirements.txt                   # фикс. версии зависимостей
    ├── .streamlit/config.toml             # тема веб-интерфейса
    ├── docs/                              # документация
    ├── src/
    │   ├── agents/                        # 6 агентов пайплайна
    │   ├── app/                           # оркестратор
    │   ├── web/                           # Streamlit UI
    │   └── utils/                         # LLM-клиент
    ├── tasks/                             # копии заданий хакатона
    └── ETHICS.md

## Пример клинического вопроса

> Какова эффективность osimertinib при NSCLC с мутацией EGFR T790M после прогрессии на гефитинибе?

Система:
1. Структурирует в PICO (Population: NSCLC с T790M после гефитиниба; Intervention: osimertinib; Outcomes: ВБП/ОВ/ORR)
2. Запрашивает PubMed по 3 разным формулировкам (broad / specific / trials_focused)
3. Находит AURA3 (PMID 27959700, NEJM 2017), финальный анализ ОВ (PMID 32861806), японскую подгруппу (PMID 29697876)
4. Включает 3 РКИ высокого качества, исключает обзоры и preclinical
5. Делает Scoping (knowledge gaps), оценивает возможность метаанализа
6. Формирует отчёт: HR 0.30 для ВБП, ORR 71% vs 31%, обсуждение crossover

## Лицензия

[MIT](LICENSE)

## Команда

- Леонид Максимюк — архитектура, агенты, веб-интерфейс
- Andrey Syrchin — участник команды

---

Дисклеймер: этот ассистент не заменяет клинические рекомендации. Решения принимает врач, опираясь на актуальные guidelines (NCCN, ESMO, RUSSCO).