"""Главный оркестратор: вопрос → Verifier → Researcher → Scoping → Critic → Meta-Checker → Synthesizer → отчёт."""
from openai import OpenAI

from src.agents.verifier import verify_question
from src.agents.researcher import search_pubmed_direct
from src.agents.scoping import scope_field
from src.agents.critic import critique_sources
from src.agents.meta_checker import check_meta_feasibility
from src.agents.synthesizer import synthesize_report


def run_pipeline(client: OpenAI, question: str, max_sources: int = 10, verbose: bool = True) -> dict:
    """Полный аналитический пайплайн.
    
    Args:
        client: OpenAI-клиент, настроенный на Yandex AI Studio (от get_client())
        question: свободный вопрос врача
        max_sources: максимум источников для поиска
        verbose: печатать ли промежуточные шаги
    
    Returns:
        dict с полями: pico, sources, scoping, critiques, meta_check, report
    """
    if verbose:
        print("=" * 60)
        print("Шаг 1/6: Verifier — структурирование вопроса в PICO")
        print("=" * 60)
    
    try:
        pico = verify_question(client, question)
    except Exception as e:
        return {
            "pico": {},
            "sources": [],
            "critiques": [],
            "report": f"Ошибка на этапе Verifier: {e}\n\nПопробуйте переформулировать вопрос."
        }
    
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
        print(f"Search queries: {len(pico.get('search_queries', {}))} разных запросов")
        print()
        print("=" * 60)
        print("Шаг 2/6: Researcher — поиск в PubMed")
        print("=" * 60)
    
    # Запускаем 3 разных запроса, объединяем уникальные источники
    queries = pico.get("search_queries", {})
    seen_pmids = set()
    sources = []
    failed_queries = 0
    
    per_query_limit = max(3, max_sources // 3)
    
    for query_type, query in queries.items():
        if not query:
            continue
        if verbose:
            print(f"  [{query_type}] {query}")
        batch = search_pubmed_direct(query, max_results=per_query_limit)
        if not batch:
            failed_queries += 1
        for s in batch:
            pmid = s.get("pmid")
            if pmid and pmid not in seen_pmids:
                seen_pmids.add(pmid)
                sources.append(s)
        if len(sources) >= max_sources:
            break
    
    sources = sources[:max_sources]
    if verbose:
        print(f"Найдено источников: {len(sources)}")
        for s in sources:
            print(f"  PMID {s['pmid']} ({s['year']}): {s['title'][:80]}")
        print()
    
    if not sources:
        total_queries = len([q for q in queries.values() if q])
        if failed_queries == total_queries and total_queries > 0:
            err_msg = (
                "Не удалось получить данные из PubMed (возможно, временные проблемы сети "
                "или лимит запросов). Попробуйте позже."
            )
        else:
            err_msg = (
                "По данному запросу источников в PubMed не найдено. "
                "Попробуйте переформулировать вопрос или использовать более общие термины."
            )
        return {
            "pico": pico,
            "sources": [],
            "critiques": [],
            "report": err_msg
        }
    
    if verbose:
        print("=" * 60)
        print("Шаг 3/6: Scoping — обзор научного поля")
        print("=" * 60)
    
    try:
        scoping = scope_field(client, pico, sources)
    except Exception as e:
        if verbose:
            print(f"[WARN] Scoping не выполнен: {e}")
        scoping = {}
    
    if verbose:
        pub_types = scoping.get("publication_types", {})
        print(f"Типы публикаций: {pub_types}")
        gaps = scoping.get("knowledge_gaps", [])
        if gaps:
            print(f"Пробелы в исследованиях:")
            for gap in gaps:
                print(f"  - {gap}")
        print()
        print("=" * 60)
        print("Шаг 4/6: Critic — оценка качества каждого источника")
        print("=" * 60)
    
    try:
        critiques = critique_sources(client, pico, sources)
    except Exception as e:
        return {
            "pico": pico,
            "sources": sources,
            "scoping": scoping,
            "critiques": [],
            "report": f"Ошибка на этапе Critic: {e}"
        }
    
    if verbose:
        included = sum(1 for c in critiques if c.get("include"))
        excluded = len(critiques) - included
        print(f"Оценено: {len(critiques)}, включено: {included}, исключено: {excluded}")
        for c in critiques:
            include_mark = "+" if c.get("include") else "-"
            print(f"  [{include_mark}] PMID {c.get('pmid')} — {c.get('study_type')} L{c.get('evidence_level')}")
        print()
        print("=" * 60)
        print("Шаг 5/6: Meta-Checker — оценка возможности метаанализа")
        print("=" * 60)
    
    try:
        meta_check = check_meta_feasibility(client, pico, critiques, sources)
    except Exception as e:
        if verbose:
            print(f"[WARN] Meta-Checker не выполнен: {e}")
        meta_check = {}
    
    if verbose:
        print(f"Метаанализ: {meta_check.get('feasibility_label', '—')}")
        print(f"Включённых РКИ: {meta_check.get('n_rcts', 0)}")
        rec = meta_check.get('recommendation', '')
        if rec:
            print(f"Рекомендация: {rec}")
        print()
        print("=" * 60)
        print("Шаг 6/6: Synthesizer — формирование отчёта")
        print("=" * 60)
    
    try:
        report = synthesize_report(client, pico, critiques, sources, scoping=scoping, meta_check=meta_check)
    except Exception as e:
        return {
            "pico": pico,
            "sources": sources,
            "scoping": scoping,
            "critiques": critiques,
            "meta_check": meta_check,
            "report": f"Ошибка на этапе Synthesizer: {e}"
        }
    
    if verbose:
        print("Отчёт сгенерирован.")
        print()
    
    return {
        "pico": pico,
        "sources": sources,
        "scoping": scoping,
        "critiques": critiques,
        "meta_check": meta_check,
        "report": report
    }
