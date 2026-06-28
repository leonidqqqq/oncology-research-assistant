"""Прогон бенчмарка качества AI-ассистента.

Запуск: python -m benchmarks.run_benchmark
Результаты: benchmarks/results.md
"""
from dotenv import load_dotenv
load_dotenv()

import json
import time
from datetime import datetime
from pathlib import Path

from src.utils.llm_client import get_client
from src.agents.verifier import verify_question
from src.agents.researcher import search_pubmed_direct
from src.agents.critic import critique_sources

CASES_FILE = Path(__file__).parent / "cases.json"
RESULTS_FILE = Path(__file__).parent / "results.md"
MAX_SOURCES = 10


def run_case(client, case: dict) -> dict:
    """Прогоняет один кейс и возвращает метрики."""
    question = case["question"]
    landmark_pmids = set(case["landmark_pmids"])
    
    print(f"\n{'=' * 70}")
    print(f"[{case['id']}] {question[:80]}...")
    print(f"Landmark PMIDs: {landmark_pmids}")
    
    t0 = time.time()
    
    # Шаг 1: PICO
    try:
        pico = verify_question(client, question)
    except Exception as e:
        return {"id": case["id"], "error": f"Verifier failed: {e}", "elapsed_s": round(time.time() - t0, 1)}
    
    if not pico.get("is_answerable"):
        return {
            "id": case["id"],
            "error": f"PICO not answerable: {pico.get('clarification_needed', '')}",
            "elapsed_s": round(time.time() - t0, 1)
        }
    
    # Шаг 2: PubMed (как в pipeline.py)
    queries = pico.get("search_queries", {})
    seen_pmids = set()
    sources = []
    per_query_limit = max(3, MAX_SOURCES // 3)
    
    for query_type, query in queries.items():
        if not query:
            continue
        batch = search_pubmed_direct(query, max_results=per_query_limit)
        for s in batch:
            pmid = s.get("pmid")
            if pmid and pmid not in seen_pmids:
                seen_pmids.add(pmid)
                sources.append(s)
        if len(sources) >= MAX_SOURCES:
            break
    
    found_pmids = {s["pmid"] for s in sources}
    
    # Шаг 3: Critic
    included_count = 0
    try:
        critiques = critique_sources(client, pico, sources)
        included_count = sum(1 for c in critiques if c.get("include", False))
    except Exception as e:
        return {
            "id": case["id"],
            "error": f"Critic failed: {e}",
            "total_found": len(sources),
            "elapsed_s": round(time.time() - t0, 1),
        }
    
    landmark_found = landmark_pmids & found_pmids
    recall = len(landmark_found) / len(landmark_pmids) if landmark_pmids else 0.0
    
    return {
        "id": case["id"],
        "question_short": question[:120],
        "total_found": len(sources),
        "included_after_critic": included_count,
        "landmark_pmids": sorted(landmark_pmids),
        "landmark_found": sorted(landmark_found),
        "recall_at_10": round(recall, 2),
        "elapsed_s": round(time.time() - t0, 1),
    }


def format_results(all_results: list, cases_meta: dict) -> str:
    lines = [
        "# Бенчмарк качества AI-ассистента",
        "",
        f"**Дата прогона**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Версия кейсов**: {cases_meta.get('version', '1.0')}",
        "",
        "## Метрика",
        "",
        "**Recall@10** — доля landmark PMID (известных эталонных РКИ), найденных в top-10 результатах Researcher.",
        "Recall@10 = 1.0 означает, что все эталонные исследования были найдены.",
        "",
        "## Сводная таблица",
        "",
        "| Case | Recall@10 | Found/Total Landmarks | Total Sources | Included after Critic | Time |",
        "|---|---|---|---|---|---|",
    ]
    
    total_recall = 0.0
    successful = 0
    
    for r in all_results:
        if "error" in r:
            lines.append(f"| {r['id']} | ❌ ERROR | — | — | — | {r['elapsed_s']:.1f}s |")
            continue
        successful += 1
        total_recall += r["recall_at_10"]
        emoji = "✅" if r["recall_at_10"] == 1.0 else ("🟡" if r["recall_at_10"] > 0 else "❌")
        lines.append(
            f"| {r['id']} | {emoji} {r['recall_at_10']:.2f} "
            f"| {len(r['landmark_found'])}/{len(r['landmark_pmids'])} "
            f"| {r['total_found']} | {r['included_after_critic']} | {r['elapsed_s']:.1f}s |"
        )
    
    avg = total_recall / successful if successful else 0.0
    lines.extend([
        "",
        f"**Средний Recall@10**: **{avg:.2f}** ({successful}/{len(all_results)} кейсов успешно)",
        "",
        "## Детали",
        "",
    ])
    
    for r in all_results:
        lines.append(f"### {r['id']}")
        if "error" in r:
            lines.append(f"❌ **Ошибка**: {r['error']}")
            lines.append("")
            continue
        lines.append(f"- **Вопрос**: {r['question_short']}")
        lines.append(f"- **Recall@10**: {r['recall_at_10']:.2f}")
        lines.append(f"- **Landmark эталон**: {', '.join(r['landmark_pmids'])}")
        lines.append(f"- **Landmark найдено**: {', '.join(r['landmark_found']) if r['landmark_found'] else '—'}")
        lines.append(f"- **Всего источников**: {r['total_found']}")
        lines.append(f"- **Включено после Critic**: {r['included_after_critic']}")
        lines.append(f"- **Время**: {r['elapsed_s']:.1f}s")
        lines.append("")
    
    return "\n".join(lines)


def main():
    with open(CASES_FILE, encoding="utf-8") as f:
        data = json.load(f)
    
    cases = data["cases"]
    print(f"Прогон бенчмарка: {len(cases)} кейсов, MAX_SOURCES={MAX_SOURCES}")
    print(f"Ожидаемое время: ~{len(cases) * 3} минут")
    
    client = get_client()
    
    all_results = []
    t_start = time.time()
    
    for case in cases:
        result = run_case(client, case)
        all_results.append(result)
        if "error" in result:
            print(f"  ❌ {result['error']}")
        else:
            print(f"  ✅ Recall@10: {result['recall_at_10']:.2f} | "
                  f"Found {len(result['landmark_found'])}/{len(result['landmark_pmids'])} | "
                  f"Sources {result['total_found']} | Time {result['elapsed_s']:.1f}s")
    
    print(f"\n{'=' * 70}")
    print(f"Общее время: {(time.time() - t_start) / 60:.1f} мин")
    
    report = format_results(all_results, data)
    RESULTS_FILE.write_text(report, encoding="utf-8")
    print(f"Результаты: {RESULTS_FILE}")
    
    json_path = RESULTS_FILE.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "results": all_results}, f, ensure_ascii=False, indent=2)
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
