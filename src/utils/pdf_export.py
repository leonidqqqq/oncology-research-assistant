"""Конвертация markdown-отчёта в PDF через xhtml2pdf с поддержкой кириллицы.

Использует DejaVu Sans, разрешённый через link_callback (стандартный механизм xhtml2pdf
для подключения ресурсов из локальной файловой системы).
"""
from io import BytesIO
from pathlib import Path

import markdown
from xhtml2pdf import pisa


_FONT_DIR = Path(__file__).resolve().parents[1] / "web" / "fonts"
_FONT_FILE = "DejaVuSans.ttf"


def _link_callback(uri: str, rel: str) -> str:
    """xhtml2pdf вызывает этот колбэк для каждого ресурса (шрифт, картинка).
    
    Перехватываем запросы к нашему шрифту и возвращаем абсолютный путь.
    """
    if uri.endswith(_FONT_FILE):
        return str(_FONT_DIR / _FONT_FILE)
    return uri


PDF_CSS = """
@font-face {
    font-family: "DejaVu";
    src: url("DejaVuSans.ttf");
}
@page {
    size: A4;
    margin: 2cm;
}
body, p, li, td, th, h1, h2, h3, h4, strong, b, em, i, blockquote, div {
    font-family: "DejaVu", Helvetica, sans-serif;
}
body {
    line-height: 1.5;
    color: #1a1a1a;
    font-size: 10pt;
}
h1 {
    font-size: 18pt;
    color: #1a3a6c;
    border-bottom: 2px solid #4A90E2;
    padding-bottom: 6px;
    margin-top: 18pt;
}
h2 {
    font-size: 14pt;
    color: #2c5282;
    margin-top: 16pt;
}
h3 {
    font-size: 11pt;
    color: #2d3748;
    margin-top: 12pt;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 10pt 0;
    font-size: 9pt;
}
th, td {
    border: 1px solid #ccc;
    padding: 6pt 8pt;
    text-align: left;
    vertical-align: top;
}
th {
    background: #e2e8f0;
    font-weight: bold;
}
blockquote {
    border-left: 3px solid #4A90E2;
    padding-left: 10pt;
    color: #555;
    margin: 10pt 0;
}
"""


def report_to_pdf(report_md: str, question: str = "") -> bytes:
    """Конвертирует markdown-отчёт в PDF."""
    html_body = markdown.markdown(
        report_md,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    
    header = ""
    if question:
        header = (
            '<h1>AI-ассистент онкологических исследований</h1>'
            f'<p><strong>Клинический вопрос:</strong> {question}</p>'
            '<hr/>'
        )
    
    html_full = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <style>{PDF_CSS}</style>
</head>
<body>
{header}
{html_body}
</body>
</html>"""
    
    buf = BytesIO()
    result = pisa.CreatePDF(
        html_full,
        dest=buf,
        encoding="utf-8",
        link_callback=_link_callback,
    )
    
    if result.err:
        raise RuntimeError(f"xhtml2pdf вернул {result.err} ошибок")
    
    buf.seek(0)
    return buf.read()
