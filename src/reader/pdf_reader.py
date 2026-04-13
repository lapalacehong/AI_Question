"""
PDF 文件读取器，使用 PyMuPDF (fitz) 提取文本。
"""
from pathlib import Path

from reader.base import ReaderResult, truncate_content


def read_pdf(filepath: str) -> ReaderResult:
    """读取 PDF 文件并提取纯文本。"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "读取 PDF 需要 PyMuPDF 库。\n"
            "  安装方法: uv add PyMuPDF"
        )

    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"文件未找到: {p}")

    doc = fitz.open(str(p))
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()

    text = "\n\n".join(pages).strip()
    if not text:
        raise ValueError(f"PDF 文件中未提取到文本: {p}")

    content, truncated = truncate_content(text)
    return ReaderResult(
        content=content,
        source_label=p.name,
        source_type="pdf",
        truncated=truncated,
    )
