"""Главный оркестратор: вопрос → Verifier → Researcher → Critic → Synthesizer → отчёт."""
from google import genai

from src.agents.verifier import verify_question
from src.agents.researcher import search_pubmed_direct
from src.agents.critic import critique_sources
from src.agents.synthesizer import synthesize_report


def run_pipeline(client: genai.Client, question: str, max_sources: int = 10, verbose: bool = True) -> dict:
    """Полный аналитический пайплайн.
    
    Args:
        client: клиент Gemini
        question: свободный вопрос врача
        max_sources: максимум источников для поиска
        verbose: печатать ли промежуточные шаги
    
    Returns:
        dict с полями: pico, sources, critiques, report
    """
    if verbose:
        print("=" * 60)
        print("Шаг 1/4: Verifier — структурирование вопроса в PICO")
        print("=" * 60)
    
    pico = verify_question(client, question)
    
    if not pico.get("is_answerable"):
        return {
            "pico": pico,
            "sources": [],
            "critiques": [],
            "report": f"Вопрос требует уточнения: {pico.get('clarification_needed', '')}"
        }
    
    if verbose:
        print(f"Population: {pico.get('population', '')}")
        print(f"Intervention: {pico.get('intervention', '')}")
        print(f"Comparator: {pico.get('comparator', '')}")
        print(f"Outcomes: {pico.get('outcomes', '')}")
        print(f"Search query: {pico.get('search_query', '')}")
        print()
        print("=" * 60)
        print("Шаг 2/4: Researcher — поиск в PubMed")
        print("=" * 60)
    
    sources = search_pubmed_direct(pico["search_query"], max_results=max_sources)
    
    if verbose:
        print(f"Найдено источников: {len(sources)}")
        for s in sources:
            print(f"  PMID {s['pmid']} ({s['year']}): {s['title'][:80]}")
        print()
    
    if not sources:
        return {
            "pico": pico,
            "sources": [],
            "critiques": [],
            "report": "По данному запросу источников в PubMed не найдено."
        }
    
    if verbose:
        print("=" * 60)
        print("Шаг 3/4: Critic — оценка качества каждого источника")
        print("=" * 60)
    
    critiques = critique_sources(client, pico, sources)
    
    if verbose:
        included = sum(1 for c in critiques if c.get("include"))
        excluded = len(critiques) - included
        print(f"Оценено: {len(critiques)}, включено: {included}, исключено: {excluded}")
        for c in critiques:
            include_mark = "+" if c.get("include") else "-"
            print(f"  [{include_mark}] PMID {c.get('pmid')} — {c.get('study_type')} L{c.get('evidence_level')}")
        print()
        print("=" * 60)
        print("Шаг 4/4: Synthesizer — формирование отчёта")
        print("=" * 60)
    
    report = synthesize_report(client, pico, critiques, sources)
    
    if verbose:
        print("Отчёт сгенерирован.")
        print()
    
    return {
        "pico": pico,
        "sources": sources,
        "critiques": critiques,
        "report": report
    }