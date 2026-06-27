"""Общий клиент для Yandex AI Studio через OpenAI-совместимый API."""
import os
import time
from openai import OpenAI


YANDEX_BASE_URL = "https://llm.api.cloud.yandex.net/v1"

# Распределение моделей по агентам
MODEL_FOR_AGENT = {
    "verifier": "yandexgpt/rc",
    "critic": "yandexgpt/rc",
    "scoping": "yandexgpt/rc",
    "synthesizer": "qwen3-235b-a22b-fp8/latest",
}

# Таймаут одного запроса в секундах. Yandex обычно отвечает за 5-30 сек.
# 120 — буфер на длинные ответы Synthesizer.
LLM_TIMEOUT_SECONDS = 120

# Задержки между retry-попытками
RETRY_DELAYS = [2, 5, 12]


def get_client() -> OpenAI:
    """Создаёт OpenAI-клиент, настроенный на Yandex AI Studio."""
    api_key = os.getenv("YANDEX_API_KEY")
    if not api_key:
        raise RuntimeError("YANDEX_API_KEY не найден в окружении (.env)")
    
    return OpenAI(
        api_key=api_key,
        base_url=YANDEX_BASE_URL,
        timeout=LLM_TIMEOUT_SECONDS,
    )


def get_model_uri(agent: str) -> str:
    """Возвращает полный URI модели для указанного агента."""
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    if not folder_id:
        raise RuntimeError("YANDEX_FOLDER_ID не найден в окружении (.env)")
    
    model = MODEL_FOR_AGENT.get(agent)
    if not model:
        raise ValueError(f"Неизвестный агент: {agent}")
    
    return f"gpt://{folder_id}/{model}"


def call_llm(
    client: OpenAI,
    agent: str,
    system_prompt: str,
    user_message: str,
    temperature: float = 0.2,
    max_tokens: int = 4000,
    max_retries: int = 3,
    response_format_json: bool = False,
) -> str:
    """Универсальный вызов LLM с retry на временных ошибках.
    
    Args:
        client: OpenAI-клиент (от get_client())
        agent: один из verifier/critic/scoping/synthesizer
        system_prompt: системное сообщение (роль, инструкции)
        user_message: пользовательское сообщение (данные для обработки)
        temperature: 0.0-1.0, для структурированных задач ставь 0.1-0.2
        max_tokens: лимит выходных токенов
        max_retries: число попыток при сбое (429, 503, network)
        response_format_json: если True — попросить вернуть JSON.
            ВНИМАНИЕ: Yandex AI Studio часто возвращает невалидный JSON в этом режиме
            для русского текста — лучше использовать собственный _extract_json() в агентах.
    
    Returns:
        строка с ответом модели (никогда не None — при пустом ответе возвращает "").
    
    Raises:
        RuntimeError: если все попытки исчерпаны
    """
    model_uri = get_model_uri(agent)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    
    kwargs = {
        "model": model_uri,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    if response_format_json:
        kwargs["response_format"] = {"type": "json_object"}
    
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(**kwargs)
            
            # Защита от пустого ответа
            if not response.choices:
                last_error = "API вернул пустой choices"
                if attempt < max_retries - 1:
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                raise RuntimeError(f"[{agent}] API вернул пустой ответ после {max_retries} попыток")
            
            content = response.choices[0].message.content
            return content or ""
            
        except Exception as e:
            last_error = e
            err_str = str(e)
            
            # Ретраим только на временных ошибках
            retriable_markers = ["429", "503", "504", "timeout", "TIMEOUT", "Connection", "connection"]
            is_retriable = any(marker in err_str for marker in retriable_markers)
            
            if is_retriable and attempt < max_retries - 1:
                wait = RETRY_DELAYS[attempt]
                print(f"[{agent}] Временная ошибка (попытка {attempt+1}/{max_retries}): {err_str[:200]}")
                print(f"[{agent}] Жду {wait} сек и повторяю...")
                time.sleep(wait)
                continue
            
            # Не retriable или попытки исчерпаны
            raise
    
    raise RuntimeError(f"[{agent}] Не удалось выполнить запрос после {max_retries} попыток: {last_error}")
