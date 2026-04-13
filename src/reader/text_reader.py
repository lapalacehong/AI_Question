"""
文本文件读取器，支持 TXT / MD / TEX 格式。
"""
import re
from pathlib import Path

from reader.base import ReaderResult, truncate_content


def read_text(filepath: str) -> ReaderResult:
    """读取文本文件并返回内容。"""
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"文件未找到: {p}")

    text = p.read_text(encoding="utf-8")

    # 对 .tex 文件，去除 preamble（\documentclass ... \begin{document}）
    if p.suffix.lower() == ".tex":
        match = re.search(r'\\begin\{document\}', text)
        if match:
            text = text[match.end():].strip()
        # 去除 \end{document}
        text = re.sub(r'\\end\{document\}\s*$', '', text).strip()

    content, truncated = truncate_content(text)
    return ReaderResult(
        content=content,
        source_label=p.name,
        source_type="text",
        truncated=truncated,
    )
