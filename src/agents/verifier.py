"""Verifier-агент: структурирует свободный вопрос врача в PICO."""
import json
from google import genai
from google.genai import types


VERIFIER_PROMPT = """Ты — Verifier-агент в системе AI-ассистента для онкологов.
Твоя задача — структурировать свободный вопрос врача в формат PICO.

PICO:
- Population: какая популяция пациентов (диагноз, стадия, возраст, биомаркеры)
- Intervention: какое вмешательство оценивается (препарат, дозировка, линия терапии)
- Comparator: с чем сравнивается (стандарт лечения, плацебо, другая терапия). Может отсутствовать.
- Outcomes: какие исходы оцениваются (ВБП, ОВ, ORR, токсичность, качество жизни)

Также определи:
- search_query: оптимальный поисковый запрос на английском для PubMed
- is_answerable: можно ли на этот вопрос ответить через анализ литературы (true/false)
- clarification_needed: если is_answerable=false, что нужно уточнить у врача

ВЫВОДИ СТРОГО JSON без markdown-обёртки, без комментариев. Формат:
{
  "population": "...",
  "intervention": "...",
  "comparator": "...",
  "outcomes": "...",
  "search_query": "...",
  "is_answerable": true,
  "clarification_needed": ""
}

Если какое-то поле PICO не указано в вопросе — пиши "not specified"."""


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
            max_output_tokens=800,
            response_mime_type="application/json"
        )
    )
    
    raw = response.text or "{}"
    
    try:
        pico = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "population": "parse error",
            "intervention": "parse error",
            "comparator": "parse error",
            "outcomes": "parse error",
            "search_query": question,
            "is_answerable": False,
            "clarification_needed": f"Не удалось распарсить PICO: {raw[:200]}"
        }
    
    return pico