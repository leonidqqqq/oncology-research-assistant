"""Verifier-агент: структурирует свободный вопрос врача в PICO."""
import json
from google import genai
from google.genai import types


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

1. broad: широкий запрос с основными терминами
   Пример: "osimertinib NSCLC T790M"
   
2. specific: более узкий, с биомаркером/линией терапии
   Пример: "osimertinib T790M resistance second-line"
   
3. trials_focused: запрос с упоминанием конкретного известного исследования
   Если знаешь имя ключевого РКИ по теме (AURA3, FLAURA, KEYNOTE-189, PACIFIC и т.д.) — 
   добавь его в запрос. Если не знаешь — добавь "randomized trial" или "phase 3".
   Пример: "AURA3 osimertinib T790M" или "osimertinib T790M randomized trial"

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


def verify_question(client: genai.Client, question: str) -> dict:
    """Структурирует вопрос врача в PICO.
    
    Args:
        client: инициализированный клиент Gemini
        question: свободный вопрос на естественном языке
    
    Returns:
        dict с полями population, intervention, comparator, outcomes,
        search_query, is_answerable, clarification_needed
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[{"role": "user", "parts": [{"text": question}]}],
        config=types.GenerateContentConfig(
            system_instruction=VERIFIER_PROMPT,
            temperature=0.1,
            max_output_tokens=2000,
            response_mime_type="application/json"
        )
    )
    
    raw = response.text or "{}"
    
    try:
        pico = json.loads(raw)
        if not isinstance(pico, dict):
            print(f"[Verifier] WARNING: ожидался dict, получили {type(pico).__name__}")
            print(f"[Verifier] Первые 300 символов: {raw[:300]}")
            raise ValueError("not a dict")
    except (json.JSONDecodeError, ValueError):
        return {
            "population": "parse error",
            "intervention": "parse error",
            "comparator": "parse error",
            "outcomes": "parse error",
            "search_queries": {
                "broad": question,
                "specific": question,
                "trials_focused": question
            },
            "is_answerable": False,
            "clarification_needed": f"Не удалось распарсить PICO: {raw[:200]}"
        }
    
    return pico