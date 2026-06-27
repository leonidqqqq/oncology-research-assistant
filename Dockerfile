FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python-зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходники
COPY src/ ./src/
COPY .streamlit/ ./.streamlit/

# Порт Streamlit
EXPOSE 8501

# Запуск веб-приложения
CMD ["streamlit", "run", "src/web/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
