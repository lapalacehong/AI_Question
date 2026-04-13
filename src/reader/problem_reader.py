"""
题目读取器（改编模式用）。
根据文件扩展名委托给 text_reader 或 pdf_reader，并标记 source_type="problem"。
"""
from pathlib import Path

from reader.base import ReaderResult


def read_problem(filepath: str) -> ReaderResult:
    """读取已有题目文件，用于改编。"""
    p = Path(filepath)
    ext = p.suffix.lower()

    if ext == ".pdf":
        from reader.pdf_reader import read_pdf
        result = read_pdf(filepath)
    else:
        from reader.text_reader import read_text
        result = read_text(filepath)

    # 将 source_type 标记为 problem
    result.source_type = "problem"
    return result
