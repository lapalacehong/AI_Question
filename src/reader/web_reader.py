"""
网页读取器，使用 httpx 抓取 + html2text 转换。
"""
from reader.base import ReaderResult, truncate_content


def read_url(url: str) -> ReaderResult:
    """抓取网页并转换为纯文本。"""
    try:
        import httpx
    except ImportError:
        raise ImportError("读取网页需要 httpx 库（通常已随 openai 安装）。")

    try:
        import html2text
    except ImportError:
        raise ImportError(
            "读取网页需要 html2text 库。\n"
            "  安装方法: uv add html2text"
        )

    resp = httpx.get(url, timeout=30, follow_redirects=True, headers={
        "User-Agent": "Mozilla/5.0 (compatible; PhysicsGenerator/1.0)"
    })
    resp.raise_for_status()

    converter = html2text.HTML2Text()
    converter.ignore_links = True
    converter.ignore_images = True
    converter.body_width = 0  # 不自动换行

    text = converter.handle(resp.text).strip()
    if not text:
        raise ValueError(f"网页中未提取到有效文本: {url}")

    content, truncated = truncate_content(text)
    return ReaderResult(
        content=content,
        source_label=url,
        source_type="url",
        truncated=truncated,
    )
