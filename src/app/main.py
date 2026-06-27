import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from sentence_transformers import SentenceTransformer
import numpy as np

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Загружаю модель эмбеддингов...")
embedding_model = SentenceTransformer("intfloat/multilingual-e5-base")
print("Модель готова")

INDEX_FILE = Path("index.json")
if INDEX_FILE.exists():
    print("Загружаю индекс документов...")
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        local_index = json.load(f)
    print(f"Загружено {len(local_index)} кусков из локальных документов")
else:
    local_index = []
    print("Локальный индекс не найден (запусти index.py для индексации PDF)")


def search_pubmed(query: str, max_results: int = 5) -> list:
    """Поиск научных статей в PubMed (база медицинской литературы NIH).
    
    Используй для поиска статей по медицинским темам, клиническим исследованиям,
    онкологии. Запрос формулируй на английском, PubMed индексирует англоязычную литературу.
    
    Args:
        query: Поисковый запрос на английском, например "EGFR mutation lung cancer 2024"
        max_results: Максимум возвращаемых статей (от 1 до 20)
    
    Returns:
        Список словарей с полями pmid, title, abstract, year.
        Если ничего не найдено — пустой список.
    """
    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    esearch_params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "date"
    }
    r = requests.get(esearch_url, params=esearch_params, timeout=15)
    r.raise_for_status()
    pmids = r.json()["esearchresult"]["idlist"]
    
    if not pmids:
        return []
    
    efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    efetch_params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml"
    }
    r = requests.get(efetch_url, params=efetch_params, timeout=15)
    r.raise_for_status()
    
    root = ET.fromstring(r.text)
    
    results = []
    for article in root.findall(".//PubmedArticle"):
        pmid_elem = article.find(".//PMID")
        title_elem = article.find(".//ArticleTitle")
        abstract_elems = article.findall(".//AbstractText")
        year_elem = article.find(".//PubDate/Year")
        
        pmid = pmid_elem.text if pmid_elem is not None else "Unknown"
        title = title_elem.text if title_elem is not None else "No title"
        abstract = " ".join([a.text for a in abstract_elems if a.text]) if abstract_elems else "No abstract"
        year = year_elem.text if year_elem is not None else "Unknown"
        
        results.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract[:800],
            "year": year
        })
    
    return results


def search_clinicaltrials(
    condition: str,
    intervention: str = "",
    status: str = "RECRUITING",
    max_results: int = 5
) -> list:
    """Поиск клинических исследований в реестре ClinicalTrials.gov (NIH).
    
    Используй когда пользователь спрашивает про активные или прошедшие
    клинические испытания, протоколы, фазы, набор пациентов.
    
    Args:
        condition: Заболевание на английском, например "non-small cell lung cancer".
        intervention: Препарат или лечение на английском, например "osimertinib". Можно пустую строку.
        status: Статус исследования. Допустимые значения:
            - RECRUITING — набирает участников (по умолчанию)
            - ACTIVE_NOT_RECRUITING — идёт, но набор закрыт
            - COMPLETED — завершено
            - NOT_YET_RECRUITING — пока не начало
            - TERMINATED — прервано
        max_results: Максимум исследований в выдаче (1-20).
    
    Returns:
        Список словарей с полями nct_id, title, status, phase, conditions,
        interventions, start_date, brief_summary.
    """
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        "query.cond": condition,
        "filter.overallStatus": status,
        "pageSize": max_results,
        "format": "json"
    }
    if intervention:
        params["query.intr"] = intervention
    
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    
    studies = data.get("studies", [])
    
    results = []
    for study in studies:
        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status_mod = protocol.get("statusModule", {})
        cond_mod = protocol.get("conditionsModule", {})
        interv_mod = protocol.get("armsInterventionsModule", {})
        design_mod = protocol.get("designModule", {})
        desc_mod = protocol.get("descriptionModule", {})
        
        nct_id = ident.get("nctId", "Unknown")
        title = ident.get("briefTitle", "No title")
        overall_status = status_mod.get("overallStatus", "Unknown")
        start_date = status_mod.get("startDateStruct", {}).get("date", "Unknown")
        conditions = cond_mod.get("conditions", [])
        interventions_list = [i.get("name", "Unknown") for i in interv_mod.get("interventions", [])]
        phases = design_mod.get("phases", [])
        brief_summary = desc_mod.get("briefSummary", "No summary")
        
        results.append({
            "nct_id": nct_id,
            "title": title,
            "status": overall_status,
            "phase": ", ".join(phases) if phases else "N/A",
            "conditions": ", ".join(conditions) if conditions else "N/A",
            "interventions": ", ".join(interventions_list) if interventions_list else "N/A",
            "start_date": start_date,
            "brief_summary": brief_summary[:600]
        })
    
    return results


def search_local_documents(query: str, top_k: int = 5) -> list:
    """Поиск по локальной базе научных статей в формате PDF.
    
    Использует семантический поиск (по смыслу, не только по ключевым словам).
    Возвращает наиболее релевантные куски текста из загруженных документов.
    
    Используй когда вопрос про конкретные исследования, методы, выводы из 
    научной литературы, которая может быть в нашей локальной базе. 
    Не используй для общих знаний или совсем свежих публикаций — для них 
    лучше search_pubmed.
    
    Args:
        query: Поисковый запрос на английском или русском. Формулируй описательно,
            например "методы оценки качества медицинских LLM" а не "оценка".
        top_k: Сколько кусков вернуть (1-10).
    
    Returns:
        Список словарей с полями source, chunk_index, text, score.
        Score от 0 до 1, чем выше — тем более релевантный кусок.
    """
    if not local_index:
        return []
    
    query_vec = embedding_model.encode(
        "query: " + query,
        normalize_embeddings=True
    )
    
    scored = []
    for item in local_index:
        item_vec = np.array(item["embedding"])
        score = float(np.dot(query_vec, item_vec))
        scored.append({
            "source": item["source"],
            "chunk_index": item["chunk_index"],
            "text": item["text"],
            "score": round(score, 4)
        })
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


SYSTEM_PROMPT = f"""Сегодня {date.today().isoformat()}.

Ты ассистент для научного исследователя в области клинической онкологии.

У тебя есть инструменты для работы с реальными медицинскими источниками:

1. search_pubmed — поиск научных статей в PubMed (для свежей литературы, статистики).
2. search_clinicaltrials — поиск клинических исследований в ClinicalTrials.gov 
   (для информации о текущих и прошедших клинических испытаниях).
3. search_local_documents — семантический поиск по нашей локальной базе научных 
   статей (PDF-документы, проиндексированные заранее). Используй для глубокого 
   разбора методологий и выводов из работ, которые есть в локальной базе.

Стратегия выбора инструмента:
- Сначала проверь, есть ли релевантная информация в локальной базе через search_local_documents.
- Если в локальной базе нет нужного — иди в PubMed.
- Для клинических испытаний всегда используй search_clinicaltrials.

Правила:
- НЕ ВЫДУМЫВАЙ данные. Нужны конкретные числа, ссылки, NCT-идентификаторы — ищи через инструменты.
- При ссылках указывай источник: для статей из PubMed — PMID и год, для исследований — NCT ID, для локальных документов — название PDF-файла.
- Статьи и исследования 2026 года — это ТЕКУЩИЕ актуальные публикации, не "будущие".
- Если поиск ничего не нашёл — так и говори.
- Технические термины не упрощай, собеседник — специалист.
- Не давай клинических рекомендаций по лечению реальных пациентов."""


def run_judge_mode():
    """Режим для ИИ-судьи: один тестовый запрос, вывод, выход."""
    print("Solution started")
    
    test_question = "Какова эффективность osimertinib для NSCLC с мутацией EGFR T790M?"
    print(f"\nТестовый запрос: {test_question}\n")
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[{"role": "user", "parts": [{"text": test_question}]}],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=2000,
            tools=[search_pubmed, search_clinicaltrials, search_local_documents]
        )
    )
    
    answer = response.text or "(модель не вернула ответа)"
    print("Ответ ассистента:")
    print(answer)
    print("\nSolution completed successfully")


def run_chat_mode():
    """Интерактивный чат для разработки."""
    print("Чат запущен. Введи 'exit' для выхода.")
    history = []
    
    while True:
        message = input("Ты: ")
        if message == "exit":
            break
        
        history.append({"role": "user", "parts": [{"text": message}]})
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                max_output_tokens=2000,
                tools=[search_pubmed, search_clinicaltrials, search_local_documents]
            )
        )
        
        bot_reply = response.text or "(модель не вернула текстового ответа)"
        history.append({"role": "model", "parts": [{"text": bot_reply}]})
        print("Gemini: " + bot_reply)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--chat":
        run_chat_mode()
    else:
        run_judge_mode()