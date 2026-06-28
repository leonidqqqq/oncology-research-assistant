"""Тесты для pipeline.run_pipeline."""
from unittest.mock import patch, MagicMock
from src.app.pipeline import run_pipeline


def make_pico(answerable=True):
    """Создаёт валидную PICO-структуру."""
    return {
        "population": "пациенты с NSCLC",
        "intervention": "osimertinib",
        "comparator": "",
        "outcomes": "ВБП, ОВ",
        "search_queries": {
            "broad": "osimertinib NSCLC",
            "specific": "osimertinib EGFR T790M",
            "trials_focused": "osimertinib AURA3",
        },
        "is_answerable": answerable,
        "clarification_needed": "" if answerable else "Уточните диагноз",
    }


def make_source(pmid="12345"):
    """Создаёт валидный источник из PubMed."""
    return {
        "pmid": pmid,
        "title": "Test article",
        "abstract": "Test abstract with results.",
        "year": "2024",
        "journal": "Test Journal",
        "authors": "Smith J.",
        "doi": "10.1234/test",
    }


def test_pipeline_returns_clarification_when_not_answerable():
    """Если Verifier вернул is_answerable=False, pipeline должен попросить уточнение."""
    client = MagicMock()
    
    with patch("src.app.pipeline.verify_question") as verify:
        verify.return_value = make_pico(answerable=False)
        result = run_pipeline(client, "плохой вопрос", verbose=False)
    
    assert "уточнения" in result["report"].lower()
    assert result["sources"] == []
    assert result["critiques"] == []


def test_pipeline_handles_no_sources():
    """Если PubMed ничего не нашёл — выдать понятное сообщение, не падать."""
    client = MagicMock()
    
    with patch("src.app.pipeline.verify_question") as verify, \
         patch("src.app.pipeline.search_pubmed_direct") as search:
        verify.return_value = make_pico()
        search.return_value = []  # PubMed ничего не нашёл
        result = run_pipeline(client, "редкий запрос", verbose=False)
    
    # Сообщение должно быть осмысленным (не падение)
    report_lower = result["report"].lower()
    assert any(phrase in report_lower for phrase in [
        "не найдено", "не удалось", "временные проблемы", "источников"
    ])
    assert result["sources"] == []


def test_pipeline_detects_pubmed_failure():
    """Если все 3 запроса вернули [] — это сетевая проблема, не отсутствие данных."""
    client = MagicMock()
    
    with patch("src.app.pipeline.verify_question") as verify, \
         patch("src.app.pipeline.search_pubmed_direct") as search:
        verify.return_value = make_pico()
        search.return_value = []  # все запросы упали
        result = run_pipeline(client, "вопрос", verbose=False)
    
    # Сообщение должно намекать на проблемы с PubMed, а не на отсутствие данных
    assert ("временные проблемы" in result["report"].lower() 
            or "не удалось" in result["report"].lower()
            or "не найдено" in result["report"].lower())


def test_pipeline_verifier_exception_handled():
    """Если Verifier бросает исключение — pipeline возвращает ошибку, не падает."""
    client = MagicMock()
    
    with patch("src.app.pipeline.verify_question") as verify:
        verify.side_effect = Exception("LLM timeout")
        result = run_pipeline(client, "вопрос", verbose=False)
    
    assert "ошибка" in result["report"].lower()
    assert "verifier" in result["report"].lower()


def test_pipeline_full_run_with_mocks():
    """Полный прогон пайплайна с мокнутыми агентами."""
    client = MagicMock()
    
    with patch("src.app.pipeline.verify_question") as verify, \
         patch("src.app.pipeline.search_pubmed_direct") as search, \
         patch("src.app.pipeline.scope_field") as scope, \
         patch("src.app.pipeline.critique_sources") as critique, \
         patch("src.app.pipeline.check_meta_feasibility") as meta, \
         patch("src.app.pipeline.synthesize_report") as synth:
        
        verify.return_value = make_pico()
        search.return_value = [make_source("11111"), make_source("22222")]
        scope.return_value = {"publication_types": {"RCT": 2}}
        critique.return_value = [
            {"pmid": "11111", "include": True, "study_type": "RCT"},
            {"pmid": "22222", "include": False, "study_type": "narrative_review"},
        ]
        meta.return_value = {"feasibility": "not_possible", "n_rcts": 1}
        synth.return_value = "## Отчёт\nТекст."
        
        result = run_pipeline(client, "тест", verbose=False)
    
    # Проверяем что все ключи на месте
    assert "pico" in result
    assert "sources" in result
    assert "scoping" in result
    assert "critiques" in result
    assert "meta_check" in result
    assert "report" in result
    
    assert len(result["sources"]) == 2
    assert result["report"] == "## Отчёт\nТекст."
    
    # Synthesizer должен получить scoping и meta_check (мы это чинили!)
    synth.assert_called_once()
    call_kwargs = synth.call_args.kwargs
    assert call_kwargs.get("scoping") == {"publication_types": {"RCT": 2}}
    assert call_kwargs.get("meta_check") == {"feasibility": "not_possible", "n_rcts": 1}
