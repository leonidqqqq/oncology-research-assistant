"""Конвертация markdown-отчёта в PDF."""
from markdown_pdf import MarkdownPdf, Section
from io import BytesIO


PDF_CSS = """
body { font-family: 'Helvetica', sans-serif; line-height: 1.5; color: #1a1a1a; }
h1 { font-size: 22pt; color: #1a3a6c; border-bottom: 2px solid #4A90E2; padding-bottom: 6px; margin-top: 18pt; }
h2 { font-size: 16pt; color: #2c5282; margin-top: 16pt; }
h3 { font-size: 13pt; color: #2d3748; margin-top: 12pt; }
table { border-collapse: collapse; width: 100%; margin: 10pt 0; font-size: 9pt; }
th, td { border: 1px solid #ccc; padding: 6pt 8pt; text-align: left; vertical-align: top; }
th { background: #e2e8f0; font-weight: 600; }
code { background: #f4f4f4; padding: 1pt 4pt; border-radius: 3px; font-family: 'Courier', monospace; font-size: 9pt; }
blockquote { border-left: 3px solid #4A90E2; padding-left: 10pt; color: #555; margin: 10pt 0; }
"""


def report_to_pdf(report_md: str, question: str = "") -> bytes:
    """Конвертирует markdown-отчёт в PDF и возвращает bytes для скачивания.
    
    Args:
        report_md: Markdown-текст отчёта
        question: Исходный клинический вопрос (вставляется как заголовок)
    
    Returns:
        PDF-файл в виде bytes
    """
    pdf = MarkdownPdf(toc_level=2)
    
    header = ""
    if question:
        header = f"# AI-ассистент онкологических исследований\n\n**Клинический вопрос:** {question}\n\n---\n\n"
    
    pdf.add_section(Section(header + report_md, paper_size="A4"), user_css=PDF_CSS)
    
    buf = BytesIO()
    pdf.save(buf)
    return buf.getvalue()
