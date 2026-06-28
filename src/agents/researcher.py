"""Researcher: прямой поиск источников по сформированному запросу."""
import requests
import time
import xml.etree.ElementTree as ET
from typing import Optional

# Streamlit кэш — если приложение запущено под Streamlit,
# одинаковые запросы будут возвращаться из кэша (TTL 1 час).
# Это снижает нагрузку на PubMed и ускоряет повторные запросы.
try:
    import streamlit as st
    _CACHE_DECORATOR = st.cache_data(ttl=3600, show_spinner=False)
except ImportError:
    # Если streamlit недоступен (CLI-режим) — кэш не применяется
    def _CACHE_DECORATOR(func):
        return func

NCBI_TOOL = "hakatonleo3-oncology-assistant"
NCBI_EMAIL = "hakatonleo3@example.com"
USER_AGENT = f"{NCBI_TOOL}/1.0 (mailto:{NCBI_EMAIL})"

NCBI_REQUEST_DELAY = 0.4

MAX_RETRIES = 3
RETRY_DELAYS = [1, 3, 7]


def _http_get_with_retry(url: str, params: dict, timeout: int = 20) -> Optional[requests.Response]:
    """GET с retry на 503/504/429 и connection-ошибках."""
    headers = {"User-Agent": USER_AGENT}
    
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers=headers)
            
            if r.status_code in (429, 500, 502, 503, 504):
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                return None
            
            r.raise_for_status()
            return r
            
        except (requests.Timeout, requests.ConnectionError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
                continue
            return None
        except requests.HTTPError:
            return None
    
    return None


@_CACHE_DECORATOR
def search_pubmed_direct(query: str, max_results: int = 10) -> list:
    """Прямой поиск в PubMed с извлечением абстрактов.
    
    Устойчив к временным ошибкам PubMed (503/504/429/timeout): до 3 попыток
    с экспоненциальной задержкой. При полном отказе возвращает [].
    """
    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    esearch_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
        "tool": NCBI_TOOL,
        "email": NCBI_EMAIL,
    }
    
    r = _http_get_with_retry(esearch_url, esearch_params, timeout=15)
    if r is None:
        print(f"  [WARN] PubMed esearch недоступен для запроса: {query}")
        return []
    
    try:
        pmids = r.json().get("esearchresult", {}).get("idlist", [])
    except ValueError:
        print(f"  [WARN] PubMed вернул невалидный JSON для запроса: {query}")
        return []
    
    if not pmids:
        return []
    
    time.sleep(NCBI_REQUEST_DELAY)
    
    efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    efetch_params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "tool": NCBI_TOOL,
        "email": NCBI_EMAIL,
    }
    
    r = _http_get_with_retry(efetch_url, efetch_params, timeout=20)
    if r is None:
        print(f"  [WARN] PubMed efetch недоступен для запроса: {query}")
        return []
    
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError as e:
        print(f"  [WARN] PubMed вернул битый XML: {e}")
        return []
    
    results = []
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        title_el = article.find(".//ArticleTitle")
        abstract_els = article.findall(".//AbstractText")
        year_el = article.find(".//PubDate/Year")
        journal_el = article.find(".//Journal/Title")
        doi_el = article.find(".//ArticleId[@IdType='doi']")
        
        authors = []
        for author in article.findall(".//Author")[:5]:
            last = author.find("LastName")
            first = author.find("ForeName")
            if last is not None and first is not None and last.text and first.text:
                authors.append(f"{last.text} {first.text[0]}.")
        
        abstract_parts = []
        for ab in abstract_els:
            label = ab.get("Label", "")
            text = ab.text or ""
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        
        results.append({
            "pmid": pmid_el.text if pmid_el is not None else "unknown",
            "title": title_el.text if title_el is not None else "No title",
            "abstract": " ".join(abstract_parts) if abstract_parts else "No abstract",
            "year": year_el.text if year_el is not None else "unknown",
            "journal": journal_el.text if journal_el is not None else "unknown",
            "authors": ", ".join(authors),
            "doi": doi_el.text if doi_el is not None else ""
        })
    
    return results
