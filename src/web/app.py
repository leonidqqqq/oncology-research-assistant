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
from src.utils.pdf_export import report_to_pdf
from src.web.i18n import get_translations


def get_t():
    """Возвращает словарь переводов для текущего языка из session_state."""
    return get_translations(st.session_state.get("lang", "ru"))
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


MAX_HISTORY = 5


def init_session_state():
    for k in ["pico", "sources", "scoping", "critiques", "meta_check", "report"]:
        if k not in st.session_state:
            st.session_state[k] = None
    if "question" not in st.session_state:
        st.session_state.question = ""
    if "history" not in st.session_state:
        st.session_state.history = []  # список dict с предыдущими анализами
    if "lang" not in st.session_state:
        st.session_state.lang = "ru"


def save_to_history(question: str):
    """Сохраняет текущий результат анализа в историю (последние MAX_HISTORY запросов)."""
    if not st.session_state.get("report"):
        return  # не сохраняем неудачные / пустые
    
    entry = {
        "question": question,
        "pico": st.session_state.pico,
        "sources": st.session_state.sources,
        "scoping": st.session_state.scoping,
        "critiques": st.session_state.critiques,
        "meta_check": st.session_state.meta_check,
        "report": st.session_state.report,
    }
    # Удаляем дубликаты (если такой же вопрос уже был — обновляем)
    st.session_state.history = [h for h in st.session_state.history if h["question"] != question]
    st.session_state.history.insert(0, entry)
    st.session_state.history = st.session_state.history[:MAX_HISTORY]


def restore_from_history(entry: dict):
    """Восстанавливает данные предыдущего анализа в session_state."""
    st.session_state.question = entry["question"]
    for k in ["pico", "sources", "scoping", "critiques", "meta_check", "report"]:
        st.session_state[k] = entry.get(k)


def reset_results():
    for k in ["pico", "sources", "scoping", "critiques", "meta_check", "report"]:
        st.session_state[k] = None


def run_analysis(question: str, max_sources: int):
    try:
        _run_analysis_impl(question, max_sources)
    except Exception as e:
        _T = get_t()
        st.error(_T["err_analysis"].format(e=e))
        st.info(_T["err_hint"])
        st.session_state.report = None


def _run_analysis_impl(question: str, max_sources: int):
    client = get_client()
    
    progress = st.progress(0, text="Подготовка...")
    status = st.empty()
    
    T = get_t()
    status.markdown(T["step_1"])
    progress.progress(10)
    pico = verify_question(client, question)
    st.session_state.pico = pico
    
    if not pico.get("is_answerable"):
        st.session_state.report = T["warn_clarification"].format(text=pico.get("clarification_needed", ""))
        progress.progress(100)
        status.warning(st.session_state.report)
        return
    
    progress.progress(20)
    status.markdown(T["step_2"])
    
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
        st.session_state.report = T["warn_no_sources"]
        progress.progress(100)
        status.warning(st.session_state.report)
        return
    
    progress.progress(40)
    status.markdown(T["step_3"].format(n=len(sources)))
    scoping = scope_field(client, pico, sources)
    st.session_state.scoping = scoping
    
    progress.progress(60)
    status.markdown(T["step_4"])
    critiques = critique_sources(client, pico, sources)
    st.session_state.critiques = critiques
    
    progress.progress(80)
    status.markdown(T["step_5"])
    meta_check = check_meta_feasibility(client, pico, critiques, sources)
    st.session_state.meta_check = meta_check
    
    progress.progress(90)
    status.markdown(T["step_6"])
    report = synthesize_report(client, pico, critiques, sources, scoping=scoping, meta_check=meta_check)
    st.session_state.report = report
    
    progress.progress(100)
    status.empty()
    
    # Сохраняем успешный анализ в историю
    save_to_history(question)


def render_pico(pico: dict):
    T = get_t()
    st.markdown(f"## {T['pico_heading']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="pico-item">
            <div class="pico-label">{T['pico_pop']}</div>
            <div class="pico-value">{pico.get('population') or '—'}</div>
        </div>
        <div class="pico-item">
            <div class="pico-label">{T['pico_int']}</div>
            <div class="pico-value">{pico.get('intervention') or '—'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="pico-item">
            <div class="pico-label">{T['pico_comp']}</div>
            <div class="pico-value">{pico.get('comparator') or '—'}</div>
        </div>
        <div class="pico-item">
            <div class="pico-label">{T['pico_out']}</div>
            <div class="pico-value">{pico.get('outcomes') or '—'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    queries = pico.get("search_queries", {})
    if queries:
        with st.expander(T["pico_search_queries"], expanded=False):
            for qtype, q in queries.items():
                st.markdown(f"**`{qtype}`** — `{q}`")


def render_scoping(scoping: dict):
    if not scoping:
        return
    
    T = get_t()
    st.markdown(f"## {T['scoping_heading']}")
    
    summary = scoping.get("summary", "")
    if summary:
        st.markdown(f'<div class="card">{summary}</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(T["scoping_pub_types"])
        for ptype, count in scoping.get("publication_types", {}).items():
            st.markdown(f"- {ptype} — **{count}**")
    
    with col2:
        st.markdown(T["scoping_outcomes"])
        for o in scoping.get("outcomes_assessed", []):
            st.markdown(f"- {o}")
    
    with col3:
        st.markdown(T["scoping_populations"])
        for p in scoping.get("populations_studied", []):
            st.markdown(f"- {p}")
    
    interventions = scoping.get("interventions_compared", [])
    if interventions:
        st.markdown(T["scoping_interventions"])
        cols = st.columns(min(len(interventions), 3))
        for i, intv in enumerate(interventions):
            with cols[i % len(cols)]:
                st.markdown(f"- {intv}")
    
    gaps = scoping.get("knowledge_gaps", [])
    if gaps:
        st.markdown(T["scoping_gaps"])
        for gap in gaps:
            st.markdown(f"- {gap}")


def quality_badge(quality: str) -> str:
    T = get_t()
    if quality == "high":
        return f'<span class="badge badge-quality-high">{T["quality_high"]}</span>'
    if quality == "moderate":
        return f'<span class="badge badge-quality-mod">{T["quality_moderate"]}</span>'
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
    
    T = get_t()
    st.markdown(f"## {T['meta_heading']}")
    
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
            <span style="color: #8B949E;">{T["meta_included_rcts"]}: <b style="color: #E8EAED;">{n_rcts}</b></span>
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
            "homogeneous": (T["meta_homo_homogeneous"], "#2EA043"),
            "moderately_heterogeneous": (T["meta_homo_moderate"], "#D29922"),
            "heterogeneous": (T["meta_homo_heterogeneous"], "#F85149"),
        }
        with col1:
            pop_val, pop_color = homo_label_map.get(homo.get("population", ""), (homo.get("population", "—"), "#6E7681"))
            st.markdown(f"**{T['meta_population']}:** <span style='color: {pop_color};'>{pop_val}</span>", unsafe_allow_html=True)
        with col2:
            int_val, int_color = homo_label_map.get(homo.get("intervention", ""), (homo.get("intervention", "—"), "#6E7681"))
            st.markdown(f"**{T['meta_intervention']}:** <span style='color: {int_color};'>{int_val}</span>", unsafe_allow_html=True)
        
        if homo.get("notes"):
            st.markdown(f"<div style='color: #8B949E; font-size: 0.85rem; margin-top: 0.4rem;'>{homo['notes']}</div>", unsafe_allow_html=True)
    
    # Исходы с данными
    outcomes = meta_check.get("outcomes_with_enough_data", [])
    if outcomes:
        st.markdown(T["meta_outcomes_label"])
        for o in outcomes:
            quality = o.get("data_quality", "—")
            q_badge = quality_badge(quality) if quality in ("high", "moderate", "low") else f'<span class="badge badge-evidence">{quality}</span>'
            st.markdown(
                f"<div class='source-included' style='border-left-color: #2EA043;'>"
                f"<b>{o.get('outcome', '—')}</b> {q_badge} "
                f"<span style='color: #8B949E;'>· {o.get('n_studies_reporting', 0)} {T['meta_studies']}</span>"
                f"<div style='color: #8B949E; font-size: 0.85rem; margin-top: 0.3rem;'>{o.get('notes', '')}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
    
    # Ограничения
    limitations = meta_check.get("limitations", [])
    if limitations:
        st.markdown(T["meta_limitations"])
        for lim in limitations:
            st.markdown(f"- {lim}")

def render_sources(sources: list, critiques: list):
    if not sources:
        return
    
    T = get_t()
    st.markdown(f"## {T['sources_heading']}")
    
    critiques_by_pmid = {str(c.get("pmid", "")): c for c in (critiques or [])}
    included_count = sum(1 for c in (critiques or []) if c.get("include"))
    excluded_count = len(critiques or []) - included_count
    
    col1, col2, col3 = st.columns(3)
    col1.metric(T["sources_found"], len(sources))
    col2.metric(T["sources_included"], included_count)
    col3.metric(T["sources_excluded"], excluded_count)
    
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
        
        with st.expander(T["sources_details"]):
            st.markdown(f"**PubMed:** https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
            if c:
                st.markdown(f"- **{T['sources_quality_method']}:** {c.get('quality_method', '—')}")
                st.markdown(f"- **{T['sources_relevance']}:** {c.get('relevance_to_pico', '—')}")
                if not included:
                    st.markdown(f"- **{T['sources_exclude_reason']}:** {c.get('exclude_reason', '—')}")
            
            abstract = s.get("abstract", "")
            if abstract:
                st.markdown(f"**{T['sources_abstract']}**")
                st.markdown(f"> {abstract[:1000]}{'...' if len(abstract) > 1000 else ''}")


# ===== UI =====

init_session_state()

# Hero блок
_T_main = get_t()
st.markdown(f"""
<div class="hero">
    <div style="font-size: 24px !important; font-weight: 700; color: #E8EAED; margin-bottom: 8px; line-height: 1.2;">{_T_main['hero_title']}</div>
    <div class="hero-subtitle">{_T_main['hero_subtitle']}</div>
    <div class="pipeline-flow">
        Verifier → Researcher → Scoping → Critic → Meta-Checker → Synthesizer
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    # Переключатель языка
    lang_choice = st.selectbox(
        "🌐 Language / Язык",
        options=["ru", "en"],
        format_func=lambda x: "Русский" if x == "ru" else "English",
        index=0 if st.session_state.get("lang", "ru") == "ru" else 1,
        key="lang_selector",
    )
    if lang_choice != st.session_state.get("lang"):
        st.session_state.lang = lang_choice
        st.rerun()
    
    T = get_t()
    
    st.markdown(f"## {T['settings']}")
    max_sources = st.slider(
        T['max_sources'],
        min_value=5,
        max_value=20,
        value=10,
        step=1,
    )
    
    st.markdown("---")
    st.markdown(f"## {T['stack']}")
    st.markdown(T['stack_body'])
    
    # История запросов
    if st.session_state.get("history"):
        st.markdown("---")
        st.markdown(f"## {T['history']}")
        for i, entry in enumerate(st.session_state.history):
            q = entry["question"]
            short = q[:60] + "..." if len(q) > 60 else q
            if st.button(short, key=f"hist_{i}", use_container_width=True, help=q):
                restore_from_history(entry)
                st.rerun()
    
    st.markdown("---")
    st.markdown(f"## {T['ethics']}")
    st.markdown(
        f"<div style='font-size: 0.85rem; color: #8B949E;'>{T['ethics_body']}</div>",
        unsafe_allow_html=True
    )

# Поле ввода
question = st.text_area(
    _T_main['question_label'],
    value=st.session_state.question,
    height=100,
    placeholder=_T_main['question_placeholder'],
    label_visibility="visible",
)

col_run, col_reset, _ = st.columns([2, 2, 8])
with col_run:
    run_clicked = st.button(_T_main['btn_run'], type="primary")
with col_reset:
    if st.button(_T_main['btn_clear']):
        reset_results()
        st.session_state.question = ""
        st.rerun()

if run_clicked:
    if not question.strip():
        st.error(_T_main['err_empty_question'])
    else:
        st.session_state.question = question
        reset_results()
        run_analysis(question.strip(), max_sources)

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
    _T = get_t()
    st.markdown(f"## {_T['report_heading']}")
    st.markdown(st.session_state.report)
    
    col_md, col_pdf = st.columns(2)
    with col_md:
        st.download_button(
            _T["btn_download_md"],
            data=st.session_state.report,
            file_name="oncology_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_pdf:
        try:
            pdf_bytes = report_to_pdf(st.session_state.report, st.session_state.get("question", ""))
            st.download_button(
                _T["btn_download_pdf"],
                data=pdf_bytes,
                file_name="oncology_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.warning(_T["err_pdf"].format(e=e))
