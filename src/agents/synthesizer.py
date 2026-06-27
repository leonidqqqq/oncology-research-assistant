"""Synthesizer-агент: формирует финальный аналитический отчёт для врача."""
from openai import OpenAI

from src.utils.llm_client import call_llm


SYNTHESIZER_PROMPT = """Ты — Synthesizer-агент в системе AI-ассистента для онкологов.
Твоя задача — на основе PICO-структуры, оценённых источников и абстрактов
сформировать аналитический отчёт для врача-онколога.

Структура отчёта (соблюдай порядок и заголовки):

## 1. Структурированный вопрос (PICO)
Кратко: Population / Intervention / Comparator / Outcomes.

## 2. Краткий клинический вывод
2-4 предложения. Что говорят данные. Уровень определённости (высокий / умеренный / низкий / очень низкий).

## 3. Включённые исследования
Таблица в markdown:
| PMID | Дизайн | n | Год | Исход | Ключевой результат | Качество |
Опирайся ТОЛЬКО на данные из абстрактов. Если численных данных нет — пиши "не указано".

## 4. Сводка доказательной базы
- Сколько РКИ, когортных, обзоров и т.д.
- Согласованы ли результаты или противоречивы
- Что покрыто хорошо, что является пробелом

## 5. Ограничения и риски
- Что неизвестно из найденных источников
- Какие исследования могли быть упущены
- Какие предостережения для клинической практики
- ВАЖНО: явно укажи что это не клиническая рекомендация и врач должен опираться на guidelines

## 6. Диаграмма скрининга
- Найдено источников: N
- Включено: M
- Исключено: K, с разбивкой по причинам

Правила:
- Используй ТОЛЬКО данные из переданных источников. НИКАКИХ выдуманных PMID, авторов, цифр.
- Если данных недостаточно для вывода — прямо скажи "недостаточно данных".
- Отделяй факты (из источников) от интерпретации (твоей).
- Числа цитируй с указанием PMID источника.
- Пиши на русском, термины оставляй точными.
- Markdown без лишних украшений."""


def synthesize_report(client: OpenAI, pico: dict, critiques: list, sources: list) -> str:
    """Формирует финальный отчёт.
    
    Args:
        client: OpenAI-клиент, настроенный на Yandex AI Studio (от get_client())
        pico: PICO-структура
        critiques: оценки от Critic (список dict с pmid, study_type, quality, include, ...)
        sources: исходные источники с абстрактами (список dict с pmid, title, abstract, year, journal)
    
    Returns:
        Markdown-отчёт.
    """
    # Сопоставляем критики с абстрактами по PMID для удобства Synthesizer
    sources_by_pmid = {str(s.get("pmid", "")): s for s in sources}
    
    critiques_text = []
    for c in critiques:
        pmid = str(c.get("pmid", ""))
        source = sources_by_pmid.get(pmid, {})
        critiques_text.append(
            f"PMID: {pmid}\n"
            f"Title: {source.get('title', c.get('title', ''))}\n"
            f"Year: {source.get('year', '')}\n"
            f"Journal: {source.get('journal', '')}\n"
            f"Abstract: {source.get('abstract', '')[:1500]}\n"
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
    
    user_message = f"""PICO-структура:
Population: {pico.get('population', '')}
Intervention: {pico.get('intervention', '')}
Comparator: {pico.get('comparator', '')}
Outcomes: {pico.get('outcomes', '')}

Найдено источников: {len(sources)}
Оценено: {len(critiques)}

Источники с оценками Critic:

{full_sources}

Сформируй структурированный отчёт согласно инструкции."""
    
    report = call_llm(
        client=client,
        agent="synthesizer",
        system_prompt=SYNTHESIZER_PROMPT,
        user_message=user_message,
        temperature=0.2,
        max_tokens=4000,
    )
    
    return report or "Отчёт не сгенерирован."