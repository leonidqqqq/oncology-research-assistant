"""Scoping-агент: формирует обзор научного поля по теме (Scoping Review).

В отличие от систематического обзора, scoping не отбирает источники по PICO,
а картирует доступную литературу: какие типы публикаций есть, какие популяции
изучались, какие исходы оценивались, где пробелы.
"""
import json
import re
from openai import OpenAI

from src.utils.llm_client import call_llm


SCOPING_PROMPT = """Ты — Scoping-агент в системе AI-ассистента для онкологов.
Твоя задача — провести Scoping Review (обзор научного поля) на основе найденных
источников.

Scoping Review отличается от Systematic Review:
- Systematic: узкий вопрос, строгие критерии включения, оценка качества
- Scoping: картирование поля, типы публикаций, популяции, пробелы

На вход — PICO и список абстрактов с их метаданными.

Сформируй обзор по следующей структуре (вывод в JSON):

1. publication_types — словарь {тип: количество}, например {"RCT": 3, "narrative_review": 2}
2. populations_studied — список изученных популяций (стадии, биомаркеры, линии терапии),
   не дублирующий друг друга
3. outcomes_assessed — список исходов, которые изучались в найденных работах
4. interventions_compared — список вмешательств (препаратов, доз, схем), которые сравнивались
5. time_distribution — словарь {год: количество} для понимания актуальности
6. knowledge_gaps — список пробелов в исследованиях (что НЕ изучено или мало изучено),
   3-5 пунктов на естественном языке
7. summary — краткое резюме поля 2-3 предложения

ВЫВОДИ СТРОГО JSON без markdown-обёртки. Все строки на русском.
"""


def _extract_json(text: str) -> str:
    """Извлекает JSON из ответа модели, убирая markdown-обёртку."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text.strip()


def scope_field(client: OpenAI, pico: dict, sources: list) -> dict:
    """Делает scoping review на основе PICO и найденных источников.
    
    Args:
        client: OpenAI-клиент, настроенный на Yandex AI Studio (от get_client())
        pico: PICO-структура от Verifier
        sources: список найденных источников от Researcher
    
    Returns:
        dict с полями publication_types, populations_studied, outcomes_assessed,
        interventions_compared, time_distribution, knowledge_gaps, summary.
    """
    if not sources:
        return {
            "publication_types": {},
            "populations_studied": [],
            "outcomes_assessed": [],
            "interventions_compared": [],
            "time_distribution": {},
            "knowledge_gaps": ["Источников по теме не найдено"],
            "summary": "Поиск не дал результатов, scoping невозможен."
        }
    
    sources_text = "\n\n".join([
        f"[{i+1}] PMID: {s.get('pmid', 'unknown')}\n"
        f"Title: {s.get('title', '')}\n"
        f"Year: {s.get('year', '')}\n"
        f"Journal: {s.get('journal', '')}\n"
        f"Abstract: {s.get('abstract', '')[:1200]}"
        for i, s in enumerate(sources)
    ])
    
    user_message = f"""PICO-структура исследовательского вопроса:
Population: {pico.get('population', '')}
Intervention: {pico.get('intervention', '')}
Comparator: {pico.get('comparator', '')}
Outcomes: {pico.get('outcomes', '')}

Найденные источники для scoping review:

{sources_text}

Проведи scoping review согласно инструкции."""
    
    raw = call_llm(
        client=client,
        agent="scoping",
        system_prompt=SCOPING_PROMPT,
        user_message=user_message,
        temperature=0.2,
        max_tokens=8000,
    )
    
    cleaned = _extract_json(raw)
    
    try:
        scoping = json.loads(cleaned)
        if not isinstance(scoping, dict):
            print(f"[Scoping] WARNING: ожидался dict, получили {type(scoping).__name__}")
            return {}
        return scoping
    except json.JSONDecodeError as e:
        print(f"[Scoping] WARNING: не удалось распарсить JSON ({e})")
        print(f"[Scoping] Первые 300 символов: {raw[:300]}")
        return {}