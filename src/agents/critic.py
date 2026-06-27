"""Critic-агент: оценивает качество и релевантность найденных источников."""
import json
from google import genai
from google.genai import types


CRITIC_PROMPT = """Ты — Critic-агент в системе AI-ассистента для онкологов.
Твоя задача — оценить качество и применимость каждого найденного источника.

На вход получишь:
1. PICO-структуру исследовательского вопроса
2. Список абстрактов публикаций

Для КАЖДОГО источника определи:

1. study_type — тип исследования:
   - "RCT" (рандомизированное контролируемое испытание)
   - "non_randomized_trial" (нерандомизированное клиническое исследование)
   - "observational_cohort" (наблюдательное когортное)
   - "observational_case_control" (случай-контроль)
   - "case_series" (серия случаев)
   - "case_report" (отдельный кейс)
   - "systematic_review" (систематический обзор)
   - "meta_analysis" (метаанализ)
   - "narrative_review" (нарративный обзор)
   - "in_vitro" (лабораторное, не клиническое)
   - "preclinical_animal" (доклиническое на животных)
   - "guideline" (клиническое руководство)
   - "other"

2. evidence_level — уровень доказательности Oxford CEBM (1-5):
   - 1: систематические обзоры РКИ / метаанализы
   - 2: отдельные РКИ
   - 3: нерандомизированные контролируемые / когортные
   - 4: серии случаев, низкокачественные когортные
   - 5: экспертное мнение, in vitro, доклиника

3. quality_method — какая методика применима для оценки качества:
   - "RoB_2.0" для RCT
   - "ROBINS-I" для нерандомизированных интервенционных
   - "STROBE" для наблюдательных
   - "AMSTAR-2" для систематических обзоров
   - "not_applicable" для обзоров, in vitro, кейс-репортов

4. quality_assessment — оценка качества методики (high / moderate / low / very_low / not_assessable)
   — на основе того, что видно в абстракте (упомянуты ли рандомизация, ослепление, размер выборки, ITT-анализ)

5. relevance_to_pico — релевантность вопросу (high / medium / low):
   — совпадает ли population, intervention с PICO

6. include — true/false: включать ли в систематический обзор

7. exclude_reason — если include=false, причина (один из):
   - "wrong_population"
   - "wrong_intervention"  
   - "wrong_study_design" (например, in vitro когда нужны клинические)
   - "low_evidence_level"
   - "older_than_5_years_with_newer_data_available"
   - "duplicate"
   - ""

ВЫВОДИ СТРОГО JSON-массив без markdown-обёртки. Формат:
[
  {
    "pmid": "...",
    "title": "...",
    "study_type": "...",
    "evidence_level": 2,
    "quality_method": "RoB_2.0",
    "quality_assessment": "high",
    "relevance_to_pico": "high",
    "include": true,
    "exclude_reason": ""
  },
  ...
]"""


def critique_sources(client: genai.Client, pico: dict, sources: list) -> list:
    """Оценивает качество и релевантность найденных источников.
    
    Args:
        client: клиент Gemini
        pico: PICO-структура от Verifier
        sources: список dict с полями pmid, title, abstract, year, journal
    
    Returns:
        Список оценок для каждого источника. Длина может быть меньше входной,
        если LLM решит выкинуть очевидно нерелевантные.
    """
    if not sources:
        return []
    
    sources_text = "\n\n".join([
        f"[{i+1}] PMID: {s.get('pmid', 'unknown')}\n"
        f"Title: {s.get('title', '')}\n"
        f"Year: {s.get('year', '')}\n"
        f"Journal: {s.get('journal', '')}\n"
        f"Abstract: {s.get('abstract', '')[:1500]}"
        for i, s in enumerate(sources)
    ])
    
    user_message = f"""PICO-структура вопроса:
Population: {pico.get('population', '')}
Intervention: {pico.get('intervention', '')}
Comparator: {pico.get('comparator', '')}
Outcomes: {pico.get('outcomes', '')}

Найденные источники для оценки:

{sources_text}

Оцени каждый источник согласно инструкции."""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[{"role": "user", "parts": [{"text": user_message}]}],
        config=types.GenerateContentConfig(
            system_instruction=CRITIC_PROMPT,
            temperature=0.1,
            max_output_tokens=8000,
            response_mime_type="application/json"
        )
    )
    
    raw = response.text or "[]"
    
    try:
        assessments = json.loads(raw)
        if not isinstance(assessments, list):
            print(f"[Critic] WARNING: ответ не массив, тип: {type(assessments).__name__}")
            return []
        return assessments
    except json.JSONDecodeError as e:
        print(f"[Critic] WARNING: не удалось распарсить JSON ({e}). Длина ответа: {len(raw)} символов")
        print(f"[Critic] Первые 300 символов ответа: {raw[:300]}")
        print(f"[Critic] Последние 100 символов ответа: ...{raw[-100:]}")
        return []