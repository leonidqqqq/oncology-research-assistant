"""Словарь UI-строк для русского и английского.

Использование:
    from src.web.i18n import get_translations
    T = get_translations(lang_code)  # "ru" или "en"
    st.markdown(f"## {T['settings']}")
"""


TRANSLATIONS = {
    "ru": {
        # Sidebar
        "language_label": "Язык / Language",
        "settings": "Настройки",
        "max_sources": "Максимум источников",
        "stack": "Стек",
        "stack_body": (
            "- **LLM**: Yandex AI Studio  \n"
            "- **Поиск**: PubMed E-utilities  \n"
            "- **Методики**: PICO, RoB 2.0, ROBINS-I, STROBE, Oxford CEBM"
        ),
        "history": "История",
        "ethics": "⚠️ Этика",
        "ethics_body": (
            "Этот ассистент <b>не заменяет</b> клинические рекомендации. "
            "Решения принимает врач, опираясь на актуальные guidelines (NCCN, ESMO, RUSSCO)."
        ),
        
        # Hero
        "hero_title": "🔬 AI-ассистент онкологических исследований",
        "hero_subtitle": (
            "Мультиагентная система для систематического обзора литературы по PubMed. "
            "Принимает свободный вопрос врача, проводит структурированный анализ "
            "доказательной базы и формирует отчёт с цитированием источников."
        ),
        
        # Input
        "question_label": "Клинический вопрос",
        "question_placeholder": (
            "Какова эффективность osimertinib при NSCLC с мутацией EGFR T790M "
            "после прогрессии на гефитинибе?"
        ),
        "btn_run": "🔍 Запустить анализ",
        "btn_clear": "Очистить",
        "err_empty_question": "Введите вопрос для анализа",
        
        # Steps
        "step_1": "**Шаг 1 из 6** — Verifier структурирует вопрос в PICO",
        "step_2": "**Шаг 2 из 6** — Researcher ищет источники в PubMed",
        "step_3": "**Шаг 3 из 6** — Scoping картирует научное поле ({n} источников)",
        "step_4": "**Шаг 4 из 6** — Critic оценивает качество каждого источника",
        "step_5": "**Шаг 5 из 6** — Meta-Checker оценивает возможность метаанализа",
        "step_6": "**Шаг 6 из 6** — Synthesizer формирует доказательный отчёт",
        
        # PICO render
        "pico_heading": "Структурированный вопрос — PICO",
        "pico_pop": "Population",
        "pico_int": "Intervention",
        "pico_comp": "Comparator",
        "pico_out": "Outcomes",
        "pico_search_queries": "Поисковые запросы в PubMed",
        
        # Scoping render
        "scoping_heading": "Scoping Review — обзор научного поля",
        "scoping_pub_types": "**Типы публикаций**",
        "scoping_outcomes": "**Изучаемые исходы**",
        "scoping_populations": "**Изученные популяции**",
        "scoping_interventions": "**Сравниваемые вмешательства**",
        "scoping_gaps": "**Пробелы в исследованиях**",
        
        # Sources
        "sources_heading": "Найденные источники",
        "sources_found": "Найдено",
        "sources_included": "Включено в обзор",
        "sources_excluded": "Исключено",
        "sources_details": "Подробнее",
        "sources_quality_method": "Методика оценки",
        "sources_relevance": "Релевантность PICO",
        "sources_exclude_reason": "Причина исключения",
        "sources_abstract": "Абстракт",
        
        # Meta-Checker
        "meta_heading": "Возможность метаанализа",
        "meta_included_rcts": "Включённых РКИ",
        "meta_population": "Популяция",
        "meta_intervention": "Вмешательства",
        "meta_outcomes_label": "**Исходы с достаточностью данных**",
        "meta_studies": "исследований",
        "meta_limitations": "**Ограничения**",
        "meta_homo_homogeneous": "Однородна",
        "meta_homo_moderate": "Умеренно гетерогенна",
        "meta_homo_heterogeneous": "Гетерогенна",
        
        # Quality badges
        "quality_high": "высокое",
        "quality_moderate": "умеренное",
        
        # Final report
        "report_heading": "Финальный аналитический отчёт",
        "btn_download_md": "📄 Скачать Markdown",
        "btn_download_pdf": "📕 Скачать PDF",
        "err_pdf": "Не удалось сгенерировать PDF: {e}",
        "err_analysis": "Ошибка во время анализа: {e}",
        "err_hint": (
            "Возможные причины: проблемы с сетью (PubMed/Yandex AI Studio), "
            "превышен лимит запросов, или вопрос требует переформулировки."
        ),
        "warn_clarification": "Вопрос требует уточнения: {text}",
        "warn_no_sources": "По данному запросу источников в PubMed не найдено.",
    },
    "en": {
        # Sidebar
        "language_label": "Language",
        "settings": "Settings",
        "max_sources": "Max sources",
        "stack": "Stack",
        "stack_body": (
            "- **LLM**: Yandex AI Studio  \n"
            "- **Search**: PubMed E-utilities  \n"
            "- **Methods**: PICO, RoB 2.0, ROBINS-I, STROBE, Oxford CEBM"
        ),
        "history": "History",
        "ethics": "⚠️ Ethics",
        "ethics_body": (
            "This assistant <b>does not replace</b> clinical guidelines. "
            "Decisions are made by physicians based on current guidelines (NCCN, ESMO, RUSSCO)."
        ),
        
        # Hero
        "hero_title": "🔬 Oncology Research AI Assistant",
        "hero_subtitle": (
            "Multi-agent system for systematic literature review on PubMed. "
            "Accepts a free-form clinical question, performs structured analysis "
            "of the evidence base, and generates a report with source citations."
        ),
        
        # Input
        "question_label": "Clinical question",
        "question_placeholder": (
            "What is the efficacy of osimertinib in NSCLC with EGFR T790M mutation "
            "after progression on gefitinib?"
        ),
        "btn_run": "🔍 Run analysis",
        "btn_clear": "Clear",
        "err_empty_question": "Please enter a question to analyze",
        
        # Steps
        "step_1": "**Step 1 of 6** — Verifier structuring the question into PICO",
        "step_2": "**Step 2 of 6** — Researcher searching PubMed",
        "step_3": "**Step 3 of 6** — Scoping mapping the research field ({n} sources)",
        "step_4": "**Step 4 of 6** — Critic evaluating quality of each source",
        "step_5": "**Step 5 of 6** — Meta-Checker assessing meta-analysis feasibility",
        "step_6": "**Step 6 of 6** — Synthesizer composing evidence-based report",
        
        # PICO
        "pico_heading": "Structured question — PICO",
        "pico_pop": "Population",
        "pico_int": "Intervention",
        "pico_comp": "Comparator",
        "pico_out": "Outcomes",
        "pico_search_queries": "PubMed search queries",
        
        # Scoping
        "scoping_heading": "Scoping Review — research field overview",
        "scoping_pub_types": "**Publication types**",
        "scoping_outcomes": "**Outcomes assessed**",
        "scoping_populations": "**Populations studied**",
        "scoping_interventions": "**Interventions compared**",
        "scoping_gaps": "**Knowledge gaps**",
        
        # Sources
        "sources_heading": "Found sources",
        "sources_found": "Found",
        "sources_included": "Included",
        "sources_excluded": "Excluded",
        "sources_details": "Details",
        "sources_quality_method": "Quality assessment method",
        "sources_relevance": "PICO relevance",
        "sources_exclude_reason": "Exclusion reason",
        "sources_abstract": "Abstract",
        
        # Meta-Checker
        "meta_heading": "Meta-analysis feasibility",
        "meta_included_rcts": "Included RCTs",
        "meta_population": "Population",
        "meta_intervention": "Interventions",
        "meta_outcomes_label": "**Outcomes with sufficient data**",
        "meta_studies": "studies",
        "meta_limitations": "**Limitations**",
        "meta_homo_homogeneous": "Homogeneous",
        "meta_homo_moderate": "Moderately heterogeneous",
        "meta_homo_heterogeneous": "Heterogeneous",
        
        # Quality
        "quality_high": "high",
        "quality_moderate": "moderate",
        
        # Final report
        "report_heading": "Final analytical report",
        "btn_download_md": "📄 Download Markdown",
        "btn_download_pdf": "📕 Download PDF",
        "err_pdf": "Failed to generate PDF: {e}",
        "err_analysis": "Analysis error: {e}",
        "err_hint": (
            "Possible reasons: network issues (PubMed/Yandex AI Studio), "
            "rate limit exceeded, or the question requires reformulation."
        ),
        "warn_clarification": "Question requires clarification: {text}",
        "warn_no_sources": "No sources found in PubMed for this query.",
    },
}


def get_translations(lang_code: str = "ru") -> dict:
    """Возвращает словарь UI-строк для указанного языка."""
    return TRANSLATIONS.get(lang_code, TRANSLATIONS["ru"])
