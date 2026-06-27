"""CLI entry point для ИИ-судьи.

Запускает один тестовый прогон пайплайна и завершается.
Для интерактивного использования — см. src/web/app.py (Streamlit).
"""
import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from src.utils.llm_client import get_client
from src.app.pipeline import run_pipeline


TEST_QUESTION = (
    "Какова эффективность osimertinib при NSCLC с мутацией EGFR T790M "
    "после прогрессии на гефитинибе?"
)


def main():
    print("=" * 60)
    print("Oncology Research Assistant — CLI judge mode")
    print("=" * 60)
    print(f"Тестовый вопрос: {TEST_QUESTION}")
    print()
    
    # Проверка переменных окружения
    if not os.getenv("YANDEX_API_KEY"):
        print("ERROR: YANDEX_API_KEY не найден в .env", file=sys.stderr)
        sys.exit(1)
    if not os.getenv("YANDEX_FOLDER_ID"):
        print("ERROR: YANDEX_FOLDER_ID не найден в .env", file=sys.stderr)
        sys.exit(1)
    
    print("Solution started")
    
    try:
        client = get_client()
        result = run_pipeline(client, TEST_QUESTION, max_sources=10, verbose=True)
        
        print()
        print("=" * 60)
        print("ФИНАЛЬНЫЙ ОТЧЁТ")
        print("=" * 60)
        print(result["report"])
        print()
        print("Solution completed successfully")
        return 0
    except Exception as e:
        print(f"Solution failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
