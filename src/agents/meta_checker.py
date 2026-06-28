"""Meta-Analysis Feasibility Checker.

Не выполняет метаанализ. Оценивает, возможен ли метаанализ на основе найденных
и включённых источников, по принятым в EBM критериям (Cochrane Handbook).

Это методологически безопасный модуль — не рассчитывает forest plot и не
объединяет статистику, что требует биостатистической экспертизы.
"""
import json
import re
from openai import OpenAI

from src.utils.llm_client import call_llm, extract_json
from src.utils.logger import get_logger

log = get_logger(__name__)


META_CHECKER_PROMPT = """Ты — Meta-Analysis Feasibility Checker в системе AI-ассистента для онкологов.
Твоя задача — оценить, возможно ли провести метаанализ найденных источников.

ВАЖНО: ты НЕ выполняешь метаанализ и НЕ рассчитываешь объединённую статистику.
Ты только оцениваешь возможность его проведения по критериям Cochrane Handbook.

КРИТЕРИИ возможности метаанализа:

1. Количество РКИ: минимум 2 (предпочтительно 3+) включённых РКИ
2. Гомогенность популяции: похожая популяция (возраст, стадия, биомаркеры)
3. Один общий исход: РКИ должны измерять один и тот же исход 
   (например, ВБП — у всех; нельзя смешивать ВБП и качество жизни)
4. Сравнимые вмешательства: одинаковая интервенция или класс препаратов
5. Доступность количественных данных в абстрактах: HR/OR/RR с 95% ДИ, 
   медиана выживаемости, процент ответа

На вход получишь:
- PICO-структуру
- Список включённых источников (только с include=true от Critic)
- Их абстракты

Сформируй JSON-ответ:

{
  "feasibility": "possible" | "partially_possible" | "not_possible",
  "feasibility_label": "Возможен" | "Частично возможен" | "Невозможен",
  "n_rcts": число включённых РКИ,
  "outcomes_with_enough_data": [
    {
      "outcome": "название исхода",
      "n_studies_reporting": число РКИ с данными,
      "data_quality": "high" | "moderate" | "low",
      "notes": "комментарий"
    }
  ],
  "homogeneity_assessment": {
    "population": "homogeneous" | "moderately_heterogeneous" | "heterogeneous",
    "intervention": "homogeneous" | "moderately_heterogeneous" | "heterogeneous",
    "notes": "пояснение в 1-2 предложениях"
  },
  "limitations": [
    "пункт 1",
    "пункт 2"
  ],
  "recommendation": "2-3 предложения с рекомендацией: возможен ли метаанализ, какие условия выполнены, какие нет, что делать дальше"
}

ВЫВОДИ СТРОГО JSON без markdown-обёртки. Все строки на русском (кроме названий методик и препаратов).
"""




def check_meta_feasibility(
    client: OpenAI,
    pico: dict,
    critiques: list,
    sources: list,
) -> dict:
    """Оценивает возможность метаанализа на основе включённых источников.
    
    Args:
        client: OpenAI-клиент Yandex AI Studio
        pico: PICO-структура от Verifier
        critiques: оценки от Critic
        sources: исходные источники с абстрактами
    
    Returns:
        dict с feasibility/n_rcts/outcomes/homogeneity/limitations/recommendation
    """
    # Только включённые источники
    included_critiques = [c for c in critiques if c.get("include")]
    
    if not included_critiques:
        return {
            "feasibility": "not_possible",
            "feasibility_label": "Невозможен",
            "n_rcts": 0,
            "outcomes_with_enough_data": [],
            "homogeneity_assessment": {
                "population": "n/a",
                "intervention": "n/a",
                "notes": "Включённых источников нет."
            },
            "limitations": ["Ни одного источника не прошло критерии включения."],
            "recommendation": "Метаанализ невозможен — нет источников, прошедших критическую оценку."
        }
    
    # Сопоставляем критики с абстрактами
    sources_by_pmid = {str(s.get("pmid", "")): s for s in sources}
    
    # Считаем РКИ
    rct_count = sum(1 for c in included_critiques if c.get("study_type") == "RCT")
    
    included_text = []
    for c in included_critiques:
        pmid = str(c.get("pmid", ""))
        source = sources_by_pmid.get(pmid, {})
        included_text.append(
            f"PMID: {pmid}\n"
            f"Title: {source.get('title', '')}\n"
            f"Year: {source.get('year', '')}\n"
            f"Study type: {c.get('study_type', '')}\n"
            f"Quality: {c.get('quality_assessment', '')}\n"
            f"Abstract: {source.get('abstract', '')[:3000]}"
        )
    
    all_included = "\n\n========\n\n".join(included_text)
    
    user_message = f"""PICO-структура:
Population: {pico.get('population', '')}
Intervention: {pico.get('intervention', '')}
Comparator: {pico.get('comparator', '')}
Outcomes: {pico.get('outcomes', '')}

Включённые источники (прошедшие критическую оценку, всего {len(included_critiques)}, из них РКИ: {rct_count}):

{all_included}

Оцени возможность метаанализа согласно инструкции."""
    
    raw = call_llm(
        client=client,
        agent="scoping",  # Используем те же лимиты что для Scoping
        system_prompt=META_CHECKER_PROMPT,
        user_message=user_message,
        temperature=0.1,
        max_tokens=4000,
    )
    
    cleaned = extract_json(raw)
    
    try:
        result = json.loads(cleaned)
        if not isinstance(result, dict):
            log.warning(f"ожидался dict, получили {type(result).__name__}")
            return {}
        return result
    except json.JSONDecodeError as e:
        log.warning(f"не удалось распарсить JSON ({e})")
        log.warning(f"Первые 300 символов: {raw[:300]}")
        return {}