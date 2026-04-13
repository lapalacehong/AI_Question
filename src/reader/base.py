"""
内容提取器基础定义。
"""
from dataclasses import dataclass

from config.settings import REFERENCE_MAX_CHARS


@dataclass
class ReaderResult:
    """内容提取结果。"""
    content: str          # 提取的文本
    source_label: str     # 人类可读的来源标签（文件名或URL）
    source_type: str      # "pdf" | "url" | "text" | "problem"
    truncated: bool       # 是否被截断


def truncate_content(text: str, max_chars: int = REFERENCE_MAX_CHARS) -> tuple[str, bool]:
    """
    截断文本至 max_chars 字符。
    返回 (截断后文本, 是否截断)。
    """
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n\n[... 内容已截断 ...]", True
