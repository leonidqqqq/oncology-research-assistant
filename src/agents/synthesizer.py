"""Synthesizer-агент: формирует финальный аналитический отчёт для врача."""
from openai import OpenAI

from src.utils.llm_client import call_llm


SYNTHESIZER_PROMPT = """Ты — Synthesizer-агент в системе AI-ассистента для онкологов.
Твоя задача — на основе PICO-структуры, обзора научного поля (Scoping),
оценённых источников (Critic) и оценки возможности метаанализа (Meta-Checker)
сформировать аналитический отчёт для врача-онколога.

Структура отчёта (соблюдай порядок и заголовки):

## 1. Структурированный вопрос (PICO)
Кратко: Population / Intervention / Comparator / Outcomes.

## 2. Краткий клинический вывод
2-4 предложения. Что говорят данные. Уровень определённости (высокий / умеренный / низкий / очень низкий).

## 3. Обзор научного поля (Scoping)
- Распределение типов публикаций (РКИ / когортные / обзоры / преклинические)
- Выявленные пробелы в исследованиях
- Этот раздел опирается на Scoping-агента; не дублируй с разделом 4

## 4. Включённые исследования
Таблица в markdown:
| PMID | Дизайн | n | Год | Исход | Ключевой результат | Качество |
Опирайся ТОЛЬКО на данные из абстрактов. Если численных данных нет — пиши "не указано".

## 5. Возможность метаанализа
- Возможен ли метаанализ по найденным РКИ (используй данные Meta-Checker)
- Гомогенность популяций и интервенций
- Какие исходы доступны для пулинга
- Ограничения для метаанализа

## 6. Сводка доказательной базы
- Сколько РКИ, когортных, обзоров и т.д.
- Согласованы ли результаты или противоречивы
- Что покрыто хорошо, что является пробелом

## 7. Ограничения и риски
- Что неизвестно из найденных источников
- Какие исследования могли быть упущены
- Какие предостережения для клинической практики
- ВАЖНО: явно укажи что это не клиническая рекомендация и врач должен опираться на guidelines (NCCN, ESMO, RUSSCO)

## 8. Диаграмма скрининга (PRISMA-style)
- Найдено источников: N
- Включено: M
- Исключено: K, с разбивкой по причинам

Правила:
- Используй ТОЛЬКО данные из переданных источников и агентов. НИКАКИХ выдуманных PMID, авторов, цифр.
- Если данных недостаточно для вывода — прямо скажи "недостаточно данных".
- Отделяй факты (из источников) от интерпретации (твоей).
- Числа цитируй с указанием PMID источника.
- Пиши на русском, термины оставляй точными.
- Markdown без лишних украшений и эмодзи."""


def synthesize_report(
    client: OpenAI,
    pico: dict,
    critiques: list,
    sources: list,
    scoping: dict = None,
    meta_check: dict = None,
) -> str:
    """Формирует финальный отчёт.
    
    Args:
        client: OpenAI-клиент, настроенный на Yandex AI Studio (от get_client())
        pico: PICO-структура
        critiques: оценки от Critic (список dict с pmid, study_type, quality, include, ...)
        sources: исходные источники с абстрактами
        scoping: результаты Scoping-агента (publication_types, knowledge_gaps, ...)
        meta_check: результаты Meta-Checker (feasibility, homogeneity, n_rcts, ...)
    
    Returns:
        Markdown-отчёт.
    """
    sources_by_pmid = {str(s.get("pmid", "")): s for s in sources}
    
    critiques_text = []
    for c in critiques:
        pmid = str(c.get("pmid", ""))
        source = sources_by_pmid.get(pmid, {})
        # Полный абстракт, не обрезаем — Yandex AI Studio выдержит
        abstract = source.get('abstract', '')
        if len(abstract) > 3000:
            abstract = abstract[:3000] + "...[обрезано]"
        
        critiques_text.append(
            f"PMID: {pmid}\n"
            f"Title: {source.get('title', c.get('title', ''))}\n"
            f"Year: {source.get('year', '')}\n"
            f"Journal: {source.get('journal', '')}\n"
            f"Authors: {source.get('authors', '')}\n"
            f"DOI: {source.get('doi', '')}\n"
            f"Abstract: {abstract}\n"
            f"--- Critic assessment ---\n"
            f"Study type: {c.get('study_type', '')}\n"
            f"Evidence level: {c.get('evidence_level', '')}\n"
            f"Quality method: {c.get('quality_method', '')}\n"
            f"Quality: {c.get('quality_assessment', '')}\n"
            f"Relevance: {c.get('relevance_to_pico', '')}\n"
            f"Include: {c.get('include', '')}\n"
            f"Exclude reason: {c.get('exclude_reason', '')}"
        )
    
    full_sources = "\n\n========\n\n".join(critiques_text) if critiques_text else "Источники не найдены."
    
    # Scoping секция
    scoping_text = ""
    if scoping:
        pub_types = scoping.get("publication_types", {})
        gaps = scoping.get("knowledge_gaps", [])
        overview = scoping.get("field_overview", "")
        scoping_text = (
            f"Обзор поля: {overview}\n"
            f"Типы публикаций: {pub_types}\n"
            f"Пробелы: {gaps}\n"
        )
    else:
        scoping_text = "Scoping не выполнен."
    
    # Meta-Checker секция
    meta_text = ""
    if meta_check:
        meta_text = (
            f"Feasibility: {meta_check.get('feasibility', '')} ({meta_check.get('feasibility_label', '')})\n"
            f"Включённых РКИ: {meta_check.get('n_rcts', 0)}\n"
            f"Гомогенность: {meta_check.get('homogeneity_assessment', {})}\n"
            f"Исходы с достаточными данными: {meta_check.get('outcomes_with_enough_data', [])}\n"
            f"Ограничения: {meta_check.get('limitations', [])}\n"
            f"Рекомендация: {meta_check.get('recommendation', '')}"
        )
    else:
        meta_text = "Meta-Checker не выполнен."
    
    user_message = f"""PICO-структура:
Population: {pico.get('population', '')}
Intervention: {pico.get('intervention', '')}
Comparator: {pico.get('comparator', '')}
Outcomes: {pico.get('outcomes', '')}

=== Scoping (обзор поля) ===
{scoping_text}

=== Meta-Checker (возможность метаанализа) ===
{meta_text}

=== Найдено источников: {len(sources)} ===
=== Оценено Critic: {len(critiques)} ===

Источники с оценками Critic:

{full_sources}

Сформируй структурированный отчёт согласно инструкции."""
    
    report = call_llm(
        client=client,
        agent="synthesizer",
        system_prompt=SYNTHESIZER_PROMPT,
        user_message=user_message,
        temperature=0.2,
        max_tokens=6000,
    )
    
    return report or "Отчёт не сгенерирован."
