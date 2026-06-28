"""Тесты для extract_json из llm_client."""
from src.utils.llm_client import extract_json


def test_extract_json_markdown_fence():
    """JSON в markdown-обёртке должен быть извлечён."""
    text = '```json\n{"key": "value"}\n```'
    result = extract_json(text)
    assert result == '{"key": "value"}'


def test_extract_json_plain_fence():
    """JSON в обёртке без 'json' тоже работает."""
    text = '```\n{"a": 1}\n```'
    result = extract_json(text)
    assert result == '{"a": 1}'


def test_extract_json_with_text_around():
    """JSON среди текста должен быть извлечён."""
    text = 'Here is the result: {"x": 2} and some comment'
    result = extract_json(text)
    assert result == '{"x": 2}'


def test_extract_json_array():
    """Массив тоже извлекается, если нет объекта."""
    text = '[1, 2, 3]'
    result = extract_json(text)
    assert result == '[1, 2, 3]'


def test_extract_json_no_json_returns_original():
    """Если JSON нет, возвращается исходный текст."""
    text = 'just plain text'
    result = extract_json(text)
    assert result == 'just plain text'


def test_extract_json_handles_nested():
    """Вложенные объекты тоже работают."""
    text = '{"outer": {"inner": "value"}}'
    result = extract_json(text)
    assert '{"outer"' in result
    assert '"inner"' in result
