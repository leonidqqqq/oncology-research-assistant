"""Researcher: прямой поиск источников по сформированному запросу."""
import requests
import xml.etree.ElementTree as ET


def search_pubmed_direct(query: str, max_results: int = 10) -> list:
    """Прямой поиск в PubMed с извлечением абстрактов.
    
    Args:
        query: английский поисковый запрос
        max_results: максимум статей
    
    Returns:
        Список dict с pmid, title, abstract, year, journal, authors, doi.
    """
    # Шаг 1 — esearch: получить PMID
    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    esearch_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance"
    }
    
    r = requests.get(esearch_url, params=esearch_params, timeout=15)
    r.raise_for_status()
    pmids = r.json().get("esearchresult", {}).get("idlist", [])
    
    if not pmids:
        return []
    
    # Шаг 2 — efetch: получить абстракты
    efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    efetch_params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    }
    
    r = requests.get(efetch_url, params=efetch_params, timeout=20)
    r.raise_for_status()
    
    root = ET.fromstring(r.text)
    
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
            if last is not None and first is not None:
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