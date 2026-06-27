"""Streamlit веб-приложение для AI-ассистента онкологических исследований."""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from dotenv import load_dotenv

from src.utils.llm_client import get_client
from src.agents.verifier import verify_question
from src.agents.researcher import search_pubmed_direct
from src.agents.scoping import scope_field
from src.agents.critic import critique_sources
from src.agents.synthesizer import synthesize_report
from src.agents.meta_checker import check_meta_feasibility


load_dotenv(PROJECT_ROOT / ".env")

st.set_page_config(
    page_title="Oncology Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== Custom CSS =====
st.markdown("""
<style>
    /* Уменьшаем огромный шрифт заголовков Streamlit */
    h1, .stMarkdown h1, [data-testid="stHeading"] h1 {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.3rem !important;
        line-height: 1.2 !important;
    }
    h2, .stMarkdown h2, [data-testid="stHeading"] h2 {
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        margin-top: 1.5rem !important;
        color: #4A90E2 !important;
        line-height: 1.3 !important;
    }
    h3, .stMarkdown h3, [data-testid="stHeading"] h3 {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        margin-top: 1rem !important;
        line-height: 1.3 !important;
    }
    
    /* Hero-заголовок отдельно */
    .hero-title {
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        color: #E8EAED !important;
        margin-bottom: 0.4rem !important;
        line-height: 1.2 !important;
    }
    
    /* Карточки */
    .card {
        background: #1A1F2E;
        border: 1px solid #2A3142;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }
    
    /* Источник: включён */
    .source-included {
        background: linear-gradient(90deg, rgba(74, 144, 226, 0.08), transparent);
        border-left: 3px solid #4A90E2;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
    }
    
    /* Источник: исключён */
    .source-excluded {
        background: rgba(120, 120, 120, 0.04);
        border-left: 3px solid #555;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
        opacity: 0.75;
    }
    
    /* Бейджи */
    .badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-right: 0.4rem;
    }
    .badge-rct { background: #4A90E2; color: white; }
    .badge-quality-high { background: #2EA043; color: white; }
    .badge-quality-mod { background: #D29922; color: white; }
    .badge-quality-low { background: #6E7681; color: white; }
    .badge-evidence { background: #2A3142; color: #E8EAED; border: 1px solid #3A4252; }
    
    /* Метрики */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #888 !important;
    }
    
    /* PICO grid */
    .pico-item {
        background: #1A1F2E;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.6rem;
    }
    .pico-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #4A90E2;
        margin-bottom: 0.2rem;
    }
    .pico-value {
        font-size: 0.95rem;
        color: #E8EAED;
    }
    
    /* Уменьшаем большие отступы */
    .block-container {
        padding-top: 2rem !important;
        max-width: 1200px;
    }
    
    /* Sidebar — компактный */
    [data-testid="stSidebar"] h2 {
        color: #E8EAED !important;
        font-size: 1rem !important;
        margin-top: 0.5rem !important;
    }
    
    /* Скрываем меню Streamlit и футер */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* Hero блок */
    .hero {
        background: linear-gradient(135deg, #1A1F2E 0%, #161B26 100%);
        border: 1px solid #2A3142;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 1.5rem;
    }
    .hero-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #E8EAED;
        margin-bottom: 0.4rem;
    }
    .hero-subtitle {
        color: #8B949E;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .pipeline-flow {
        font-family: 'SF Mono', Menlo, monospace;
        font-size: 0.85rem;
        color: #4A90E2;
        margin-top: 1rem;
        padding: 0.6rem 1rem;
        background: rgba(74, 144, 226, 0.08);
        border-radius: 8px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    for k in ["pico", "sources", "scoping", "critiques", "meta_check", "report"]:
        if k not in st.session_state:
            st.session_state[k] = None
    if "question" not in st.session_state:
        st.session_state.question = ""


def reset_results():
    for k in ["pico", "sources", "scoping", "critiques", "meta_check", "report"]:
        st.session_state[k] = None


def run_analysis(question: str, max_sources: int):
    try:
        _run_analysis_impl(question, max_sources)
    except Exception as e:
        st.error(f"Ошибка во время анализа: {e}")
        st.info("Возможные причины: проблемы с сетью (PubMed/Yandex AI Studio), превышен лимит запросов, или вопрос требует переформулировки.")
        st.session_state.report = None


def _run_analysis_impl(question: str, max_sources: int):
    client = get_client()
    
    progress = st.progress(0, text="Подготовка...")
    status = st.empty()
    
    status.markdown("**Шаг 1 из 6** — Verifier структурирует вопрос в PICO")
    progress.progress(10)
    pico = verify_question(client, question)
    st.session_state.pico = pico
    
    if not pico.get("is_answerable"):
        st.session_state.report = f"Вопрос требует уточнения: {pico.get('clarification_needed', '')}"
        progress.progress(100)
        status.warning(st.session_state.report)
        return
    
    progress.progress(20)
    status.markdown("**Шаг 2 из 6** — Researcher ищет источники в PubMed")
    
    queries = pico.get("search_queries", {})
    seen_pmids = set()
    sources = []
    per_query_limit = max(3, max_sources // 3)
    
    for query_type, query in queries.items():
        if not query:
            continue
        batch = search_pubmed_direct(query, max_results=per_query_limit)
        for s in batch:
            pmid = s.get("pmid")
            if pmid and pmid not in seen_pmids:
                seen_pmids.add(pmid)
                sources.append(s)
        if len(sources) >= max_sources:
            break
    
    sources = sources[:max_sources]
    st.session_state.sources = sources
    
    if not sources:
        st.session_state.report = "По данному запросу источников в PubMed не найдено."
        progress.progress(100)
        status.warning(st.session_state.report)
        return
    
    progress.progress(40)
    status.markdown(f"**Шаг 3 из 6** — Scoping картирует научное поле ({len(sources)} источников)")
    scoping = scope_field(client, pico, sources)
    st.session_state.scoping = scoping
    
    progress.progress(60)
    status.markdown("**Шаг 4 из 6** — Critic оценивает качество каждого источника")
    critiques = critique_sources(client, pico, sources)
    st.session_state.critiques = critiques
    
    progress.progress(80)
    status.markdown("**Шаг 5 из 6** — Meta-Checker оценивает возможность метаанализа")
    meta_check = check_meta_feasibility(client, pico, critiques, sources)
    st.session_state.meta_check = meta_check
    
    progress.progress(90)
    status.markdown("**Шаг 6 из 6** — Synthesizer формирует доказательный отчёт")
    report = synthesize_report(client, pico, critiques, sources, scoping=scoping, meta_check=meta_check)
    st.session_state.report = report
    
    progress.progress(100)
    status.empty()


def render_pico(pico: dict):
    st.markdown("## Структурированный вопрос — PICO")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="pico-item">
            <div class="pico-label">Population</div>
            <div class="pico-value">{pico.get('population') or '—'}</div>
        </div>
        <div class="pico-item">
            <div class="pico-label">Intervention</div>
            <div class="pico-value">{pico.get('intervention') or '—'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="pico-item">
            <div class="pico-label">Comparator</div>
            <div class="pico-value">{pico.get('comparator') or '—'}</div>
        </div>
        <div class="pico-item">
            <div class="pico-label">Outcomes</div>
            <div class="pico-value">{pico.get('outcomes') or '—'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    queries = pico.get("search_queries", {})
    if queries:
        with st.expander("Поисковые запросы в PubMed", expanded=False):
            for qtype, q in queries.items():
                st.markdown(f"**`{qtype}`** — `{q}`")


def render_scoping(scoping: dict):
    if not scoping:
        return
    
    st.markdown("## Scoping Review — обзор научного поля")
    
    summary = scoping.get("summary", "")
    if summary:
        st.markdown(f'<div class="card">{summary}</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Типы публикаций**")
        for ptype, count in scoping.get("publication_types", {}).items():
            st.markdown(f"- {ptype} — **{count}**")
    
    with col2:
        st.markdown("**Изучаемые исходы**")
        for o in scoping.get("outcomes_assessed", []):
            st.markdown(f"- {o}")
    
    with col3:
        st.markdown("**Изученные популяции**")
        for p in scoping.get("populations_studied", []):
            st.markdown(f"- {p}")
    
    interventions = scoping.get("interventions_compared", [])
    if interventions:
        st.markdown("**Сравниваемые вмешательства**")
        cols = st.columns(min(len(interventions), 3))
        for i, intv in enumerate(interventions):
            with cols[i % len(cols)]:
                st.markdown(f"- {intv}")
    
    gaps = scoping.get("knowledge_gaps", [])
    if gaps:
        st.markdown("**Пробелы в исследованиях**")
        for gap in gaps:
            st.markdown(f"- {gap}")


def quality_badge(quality: str) -> str:
    if quality == "high":
        return '<span class="badge badge-quality-high">высокое</span>'
    if quality == "moderate":
        return '<span class="badge badge-quality-mod">умеренное</span>'
    if quality in ("low", "very_low"):
        return f'<span class="badge badge-quality-low">{quality}</span>'
    return f'<span class="badge badge-evidence">{quality}</span>'


def study_type_badge(stype: str) -> str:
    if stype == "RCT":
        return '<span class="badge badge-rct">RCT</span>'
    return f'<span class="badge badge-evidence">{stype}</span>'

def render_meta_check(meta_check: dict):
    """Отображает блок Meta-Analysis Feasibility."""
    if not meta_check:
        return
    
    st.markdown("## Возможность метаанализа")
    
    feasibility = meta_check.get("feasibility", "not_possible")
    label = meta_check.get("feasibility_label", "—")
    n_rcts = meta_check.get("n_rcts", 0)
    
    # Цвет бейджа по статусу
    color_map = {
        "possible": "#2EA043",
        "partially_possible": "#D29922",
        "not_possible": "#6E7681",
    }
    badge_color = color_map.get(feasibility, "#6E7681")
    
    st.markdown(f"""
    <div class="card">
        <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.8rem;">
            <span style="background: {badge_color}; color: white; padding: 0.3rem 0.8rem; 
                         border-radius: 8px; font-weight: 600; font-size: 0.9rem;">
                {label}
            </span>
            <span style="color: #8B949E;">Включённых РКИ: <b style="color: #E8EAED;">{n_rcts}</b></span>
        </div>
        <div style="color: #E8EAED; font-size: 0.95rem; line-height: 1.5;">
            {meta_check.get("recommendation", "")}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Гомогенность
    homo = meta_check.get("homogeneity_assessment", {})
    if homo:
        col1, col2 = st.columns(2)
        homo_label_map = {
            "homogeneous": ("Однородна", "#2EA043"),
            "moderately_heterogeneous": ("Умеренно гетерогенна", "#D29922"),
            "heterogeneous": ("Гетерогенна", "#F85149"),
        }
        with col1:
            pop_val, pop_color = homo_label_map.get(homo.get("population", ""), (homo.get("population", "—"), "#6E7681"))
            st.markdown(f"**Популяция:** <span style='color: {pop_color};'>{pop_val}</span>", unsafe_allow_html=True)
        with col2:
            int_val, int_color = homo_label_map.get(homo.get("intervention", ""), (homo.get("intervention", "—"), "#6E7681"))
            st.markdown(f"**Вмешательства:** <span style='color: {int_color};'>{int_val}</span>", unsafe_allow_html=True)
        
        if homo.get("notes"):
            st.markdown(f"<div style='color: #8B949E; font-size: 0.85rem; margin-top: 0.4rem;'>{homo['notes']}</div>", unsafe_allow_html=True)
    
    # Исходы с данными
    outcomes = meta_check.get("outcomes_with_enough_data", [])
    if outcomes:
        st.markdown("**Исходы с достаточностью данных**")
        for o in outcomes:
            quality = o.get("data_quality", "—")
            q_badge = quality_badge(quality) if quality in ("high", "moderate", "low") else f'<span class="badge badge-evidence">{quality}</span>'
            st.markdown(
                f"<div class='source-included' style='border-left-color: #2EA043;'>"
                f"<b>{o.get('outcome', '—')}</b> {q_badge} "
                f"<span style='color: #8B949E;'>· {o.get('n_studies_reporting', 0)} исследований</span>"
                f"<div style='color: #8B949E; font-size: 0.85rem; margin-top: 0.3rem;'>{o.get('notes', '')}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    
    # Ограничения
    limitations = meta_check.get("limitations", [])
    if limitations:
        st.markdown("**Ограничения**")
        for lim in limitations:
            st.markdown(f"- {lim}")

def render_sources(sources: list, critiques: list):
    if not sources:
        return
    
    st.markdown("## Найденные источники")
    
    critiques_by_pmid = {str(c.get("pmid", "")): c for c in (critiques or [])}
    included_count = sum(1 for c in (critiques or []) if c.get("include"))
    excluded_count = len(critiques or []) - included_count
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Найдено", len(sources))
    col2.metric("Включено в обзор", included_count)
    col3.metric("Исключено", excluded_count)
    
    st.markdown("")  # spacer
    
    for s in sources:
        pmid = str(s.get("pmid", ""))
        c = critiques_by_pmid.get(pmid, {})
        included = c.get("include", False)
        
        title = s.get("title", "—")
        year = s.get("year", "")
        journal = s.get("journal", "")
        study_type = c.get("study_type", "—")
        quality = c.get("quality_assessment", "—")
        evidence = c.get("evidence_level", "—")
        
        marker = "✓" if included else "○"
        css_class = "source-included" if included else "source-excluded"
        
        # Заголовок карточки
        header_html = f"""
        <div class="{css_class}">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="flex: 1;">
                    <span style="color: {'#4A90E2' if included else '#888'}; font-weight: 600; margin-right: 0.5rem;">{marker}</span>
                    <span style="color: #888; font-size: 0.85rem;">PMID {pmid} · {year}</span>
                </div>
                <div>
                    {study_type_badge(study_type)}
                    {quality_badge(quality)}
                    <span class="badge badge-evidence">L{evidence}</span>
                </div>
            </div>
            <div style="margin-top: 0.4rem; font-weight: 500;">{title}</div>
            <div style="margin-top: 0.2rem; color: #888; font-size: 0.85rem;">{journal}</div>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)
        
        with st.expander("Подробнее"):
            st.markdown(f"**PubMed:** https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
            if c:
                st.markdown(f"- **Методика оценки:** {c.get('quality_method', '—')}")
                st.markdown(f"- **Релевантность PICO:** {c.get('relevance_to_pico', '—')}")
                if not included:
                    st.markdown(f"- **Причина исключения:** {c.get('exclude_reason', '—')}")
            
            abstract = s.get("abstract", "")
            if abstract:
                st.markdown("**Абстракт**")
                st.markdown(f"> {abstract[:1000]}{'...' if len(abstract) > 1000 else ''}")


# ===== UI =====

init_session_state()

# Hero блок
st.markdown("""
<div class="hero">
    <div style="font-size: 24px !important; font-weight: 700; color: #E8EAED; margin-bottom: 8px; line-height: 1.2;">🔬 AI-ассистент онкологических исследований</div>
    <div class="hero-subtitle">
        Мультиагентная система для систематического обзора литературы по PubMed.
        Принимает свободный вопрос врача, проводит структурированный анализ доказательной базы
        и формирует отчёт с цитированием источников.
    </div>
    <div class="pipeline-flow">
        Verifier → Researcher → Scoping → Critic → Synthesizer
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## Настройки")
    max_sources = st.slider(
        "Максимум источников",
        min_value=5,
        max_value=20,
        value=10,
        step=1,
    )
    
    st.markdown("---")
    st.markdown("## Стек")
    st.markdown("""
- **LLM**: Yandex AI Studio  
- **Поиск**: PubMed E-utilities  
- **Методики**: PICO, RoB 2.0, ROBINS-I, STROBE, Oxford CEBM
    """)
    
    st.markdown("---")
    st.markdown("## ⚠️ Этика")
    st.markdown(
        "<div style='font-size: 0.85rem; color: #8B949E;'>"
        "Этот ассистент <b>не заменяет</b> клинические рекомендации. "
        "Решения принимает врач, опираясь на актуальные guidelines (NCCN, ESMO, RUSSCO)."
        "</div>",
        unsafe_allow_html=True
    )

# Поле ввода
question = st.text_area(
    "Клинический вопрос",
    value=st.session_state.question,
    height=100,
    placeholder="Какова эффективность osimertinib при NSCLC с мутацией EGFR T790M после прогрессии на гефитинибе?",
    label_visibility="visible",
)

col_run, col_reset, _ = st.columns([2, 2, 8])
with col_run:
    run_clicked = st.button("🔍 Запустить анализ", type="primary")
with col_reset:
    if st.button("Очистить"):
        reset_results()
        st.session_state.question = ""
        st.rerun()

if run_clicked:
    if not question.strip():
        st.error("Введите вопрос для анализа")
    else:
        st.session_state.question = question
        reset_results()
        try:
            run_analysis(question.strip(), max_sources)
        except Exception as e:
            st.error(f"Ошибка во время анализа: {e}")
            raise

# Результаты
if st.session_state.pico:
    render_pico(st.session_state.pico)

if st.session_state.scoping:
    render_scoping(st.session_state.scoping)

if st.session_state.sources:
    render_sources(st.session_state.sources, st.session_state.critiques)

if st.session_state.meta_check:
    render_meta_check(st.session_state.meta_check)

if st.session_state.report:
    st.markdown("## Финальный аналитический отчёт")
    st.markdown(st.session_state.report)
    
    st.download_button(
        "📥 Скачать отчёт (Markdown)",
        data=st.session_state.report,
        file_name="oncology_report.md",
        mime="text/markdown",
    )