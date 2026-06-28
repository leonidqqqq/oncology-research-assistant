"""Verifier-агент: структурирует свободный вопрос врача в PICO."""
import json
import re
from openai import OpenAI

from src.utils.llm_client import call_llm, extract_json
from src.utils.logger import get_logger

log = get_logger(__name__)


VERIFIER_PROMPT = """Ты — Verifier-агент в системе AI-ассистента для онкологов.
Твоя задача — структурировать свободный вопрос врача в формат PICO и
сгенерировать несколько поисковых запросов для покрытия разных формулировок.

PICO:
- Population: какая популяция пациентов (диагноз, стадия, возраст, биомаркеры)
- Intervention: какое вмешательство оценивается (препарат, дозировка, линия терапии)
- Comparator: с чем сравнивается (стандарт лечения, плацебо, другая терапия). Может отсутствовать.
- Outcomes: какие исходы оцениваются (ВБП, ОВ, ORR, токсичность, качество жизни)

ПОИСКОВЫЕ ЗАПРОСЫ:
Сгенерируй 3 РАЗНЫХ английских запроса для PubMed. ВАЖНО: запросы должны быть ПРОСТЫМИ — 
просто ключевые слова через пробел, БЕЗ MeSH-тегов, БЕЗ скобок, БЕЗ AND/OR, БЕЗ кавычек. 
Каждый запрос 3-6 слов.

- broad: широкий запрос с 3-4 основными терминами (препарат, диагноз, биомаркер)
- specific: узкий запрос с биомаркером/линией терапии/механизмом резистентности
- trials_focused: запрос, добавляющий название известного РКИ (если знаешь — AURA3, FLAURA, 
  KEYNOTE-189, PACIFIC и т.д.) или слова "randomized trial" или "phase 3"

Также определи:
- is_answerable: можно ли на этот вопрос ответить через анализ литературы (true/false)
- clarification_needed: если is_answerable=false, что нужно уточнить у врача

ВЫВОДИ СТРОГО JSON без markdown-обёртки. Формат:
{
  "population": "...",
  "intervention": "...",
  "comparator": "...",
  "outcomes": "...",
  "search_queries": {
    "broad": "...",
    "specific": "...",
    "trials_focused": "..."
  },
  "is_answerable": true,
  "clarification_needed": ""
}"""




def verify_question(client: OpenAI, question: str) -> dict:
    """Структурирует вопрос врача в PICO.
    
    Args:
        client: OpenAI-клиент, настроенный на Yandex AI Studio (от get_client())
        question: свободный вопрос на естественном языке
    
    Returns:
        dict с полями population, intervention, comparator, outcomes,
        search_queries, is_answerable, clarification_needed
    """
    raw = call_llm(
        client=client,
        agent="verifier",
        system_prompt=VERIFIER_PROMPT,
        user_message=question,
        temperature=0.1,
        max_tokens=2000,
    )
    
    cleaned = extract_json(raw)
    
    try:
        pico = json.loads(cleaned)
        if not isinstance(pico, dict):
            log.warning(f"ожидался dict, получили {type(pico).__name__}")
            log.warning(f"Первые 300 символов: {raw[:300]}")
            raise ValueError("not a dict")
    except (json.JSONDecodeError, ValueError) as e:
        log.warning(f"не удалось распарсить JSON ({e})")
        log.warning(f"Первые 300 символов: {raw[:300]}")
        return {
            "population": "parse error",
            "intervention": "parse error",
            "comparator": "parse error",
            "outcomes": "parse error",
            "search_queries": {
                "broad": question,
                "specific": question,
                "trials_focused": question,
            },
            "is_answerable": False,
            "clarification_needed": f"Не удалось распарсить PICO: {raw[:200]}",
        }
    
    return pico