import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import numpy as np

load_dotenv()

DOCS_DIR = Path("docs")
INDEX_FILE = Path("index.json")

print("Загружаю модель эмбеддингов...")
embedding_model = SentenceTransformer("intfloat/multilingual-e5-base")
print("Модель готова")


def read_pdf(path: Path) -> str:
    """Прочитать PDF и вернуть весь текст одной строкой."""
    reader = PdfReader(str(path))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text())
    return "\n".join(text_parts)


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list:
    """Разбить длинный текст на куски по chunk_size символов с пересечением overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    return chunks


def get_embedding(text: str) -> list:
    """Получить эмбеддинг для куска текста через локальную модель."""
    vec = embedding_model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def save_index(index: list, path: Path):
    """Сохранить индекс в JSON-файл."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)


def load_index(path: Path) -> list:
    """Загрузить индекс из JSON-файла."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_index() -> list:
    """Прочитать все PDF из docs/, разбить на куски, посчитать эмбеддинги.
    
    Сохраняет прогресс после каждой статьи — если упадёт, продолжит с того же места.
    """
    if INDEX_FILE.exists():
        print("Найден частичный индекс, продолжаю с него")
        index = load_index(INDEX_FILE)
        processed_sources = {item["source"] for item in index}
    else:
        index = []
        processed_sources = set()
    
    pdf_files = list(DOCS_DIR.glob("*.pdf"))
    print(f"Всего PDF: {len(pdf_files)}, уже обработано: {len(processed_sources)}")
    
    for pdf_path in pdf_files:
        if pdf_path.name in processed_sources:
            print(f"\n[{pdf_path.name}] уже в индексе, пропускаю")
            continue
        
        print(f"\n[{pdf_path.name}]")
        text = read_pdf(pdf_path)
        chunks = chunk_text(text)
        print(f"  кусков: {len(chunks)}, считаю эмбеддинги...")
        
        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            index.append({
                "source": pdf_path.name,
                "chunk_index": i,
                "text": chunk,
                "embedding": embedding
            })
        
        save_index(index, INDEX_FILE)
        print(f"  готово, индекс сохранён ({len(index)} кусков всего)")
    
    return index


def cosine_similarity(a: list, b: list) -> float:
    """Косинусное сходство двух векторов: число от -1 до 1."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


def search(query: str, index: list, top_k: int = 5) -> list:
    """Найти top_k самых похожих кусков на запрос query."""
    query_embedding = get_embedding(query)
    
    scored = []
    for item in index:
        score = cosine_similarity(query_embedding, item["embedding"])
        scored.append({
            "score": score,
            "source": item["source"],
            "chunk_index": item["chunk_index"],
            "text": item["text"]
        })
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# --- Главный код ---

if INDEX_FILE.exists():
    print(f"Загружаю существующий индекс из {INDEX_FILE}...")
    index = load_index(INDEX_FILE)
    print(f"Загружено кусков: {len(index)}")
    
    # Дочитываем недостающие PDF, если они появились
    processed_sources = {item["source"] for item in index}
    pdf_files = list(DOCS_DIR.glob("*.pdf"))
    missing = [p for p in pdf_files if p.name not in processed_sources]
    if missing:
        print(f"Найдено новых PDF: {len(missing)}, дочитываю...")
        index = build_index()
else:
    print("Индекса нет, строю с нуля...")
    index = build_index()

# Тестовые запросы
test_queries = [
    "multi-agent LLM systems for clinical decision support",
    "evaluation of large language models in radiation oncology",
    "patient matching for clinical trials using LLMs"
]

for query in test_queries:
    print(f"\n{'='*60}")
    print(f"ЗАПРОС: {query}")
    print('='*60)
    results = search(query, index, top_k=3)
    for r in results:
        print(f"\n[{r['score']:.4f}] {r['source']} (chunk {r['chunk_index']})")
        print(f"  {r['text'][:200]}...")