"""
内容提取器工厂。
支持 PDF、网页、文本文件和题目文件的读取。
"""
from pathlib import Path

from reader.base import ReaderResult

__all__ = ["extract_content", "ReaderResult"]


def extract_content(source: str, source_type: str | None = None) -> ReaderResult:
    """
    提取内容的统一入口。

    参数:
        source: 文件路径或URL
        source_type: 显式指定类型 ("pdf", "url", "text", "problem")，
                     为 None 时自动检测

    返回:
        ReaderResult 包含提取的文本内容
    """
    if source_type is None:
        source_type = _detect_type(source)

    if source_type == "pdf":
        from reader.pdf_reader import read_pdf
        return read_pdf(source)
    elif source_type == "url":
        from reader.web_reader import read_url
        return read_url(source)
    elif source_type == "problem":
        from reader.problem_reader import read_problem
        return read_problem(source)
    else:
        from reader.text_reader import read_text
        return read_text(source)


def _detect_type(source: str) -> str:
    """根据 source 字符串自动检测类型。"""
    if source.startswith("http://") or source.startswith("https://"):
        return "url"
    p = Path(source)
    ext = p.suffix.lower()
    if ext == ".pdf":
        return "pdf"
    return "text"
