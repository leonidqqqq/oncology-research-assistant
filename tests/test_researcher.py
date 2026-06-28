"""Тесты для researcher.search_pubmed_direct."""
from unittest.mock import patch, MagicMock
from src.agents.researcher import search_pubmed_direct, _http_get_with_retry


def test_researcher_returns_empty_on_no_pmids():
    """Если PubMed нашёл 0 статей — возвращаем []."""
    with patch("src.agents.researcher._http_get_with_retry") as get:
        # Мок esearch с пустым idlist
        mock_response = MagicMock()
        mock_response.json.return_value = {"esearchresult": {"idlist": []}}
        get.return_value = mock_response
        
        result = search_pubmed_direct("неизвестный запрос", max_results=5)
    
    assert result == []


def test_researcher_returns_empty_on_network_failure():
    """Если PubMed недоступен — возвращаем [] (не падаем)."""
    with patch("src.agents.researcher._http_get_with_retry") as get:
        get.return_value = None  # все попытки исчерпаны
        
        result = search_pubmed_direct("запрос", max_results=5)
    
    assert result == []


def test_http_retry_returns_response_on_success():
    """Успешный запрос возвращает Response с первой попытки."""
    with patch("src.agents.researcher.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = _http_get_with_retry("http://example.com", {})
    
    assert result is mock_response
    assert mock_get.call_count == 1  # без retry


def test_http_retry_retries_on_429():
    """429 Too Many Requests должен ретраиться."""
    import requests
    with patch("src.agents.researcher.requests.get") as mock_get, \
         patch("src.agents.researcher.time.sleep"):  # пропускаем sleep
        
        # Первые 2 попытки — 429, третья — успех
        fail_resp = MagicMock()
        fail_resp.status_code = 429
        
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.raise_for_status = MagicMock()
        
        mock_get.side_effect = [fail_resp, fail_resp, ok_resp]
        
        result = _http_get_with_retry("http://example.com", {})
    
    assert result is ok_resp
    assert mock_get.call_count == 3


def test_http_retry_gives_up_after_max_retries():
    """После 3 попыток сдаёмся и возвращаем None."""
    with patch("src.agents.researcher.requests.get") as mock_get, \
         patch("src.agents.researcher.time.sleep"):
        
        fail_resp = MagicMock()
        fail_resp.status_code = 503
        mock_get.return_value = fail_resp
        
        result = _http_get_with_retry("http://example.com", {})
    
    assert result is None
    assert mock_get.call_count == 3  # MAX_RETRIES
