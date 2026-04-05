"""
正则隔离器（纯 Python，不调用任何 LLM）。
三重隔离：先提取 Figure，再提取 Block 公式，最后提取 Inline 公式，防止嵌套污染。
使用 reversed() 从后向前替换，确保前面的 match.start()/end() 不会因替换而偏移。
"""
import re

from model.state import AgentState
from config.settings import (
    BLOCK_MATH_PATTERN, BLOCK_PLACEHOLDER_PREFIX, BLOCK_PLACEHOLDER_SUFFIX,
    INLINE_MATH_PATTERN, INLINE_PLACEHOLDER_PREFIX, INLINE_PLACEHOLDER_SUFFIX,
    FALLBACK_BLOCK_PATTERN,
    FIGURE_PATTERN, FIGURE_PLACEHOLDER_PREFIX, FIGURE_PLACEHOLDER_SUFFIX,
    logger,
)


def _sanitize_block_tags(text: str) -> str:
    r"""
    预处理：修正 LLM 常见的标签格式错误。
    - \end{block_math} → </block_math>
    - \begin{block_math} → <block_math>
    """
    text = re.sub(r'\\end\{block_math\}', '</block_math>', text)
    text = re.sub(r'\\begin\{block_math\s+label="([^"]+)"\}', r'<block_math label="\1">', text)
    return text


def python_parser(state: AgentState) -> dict:
    """
    正则隔离器：
    Phase 0: 预处理修正 LLM 常见的标签格式错误
    Phase 1: 提取 <figure> 标签 → 替换为 {{FIGURE_N}}
    Phase 2: 提取 <block_math> 标签 → 替换为 {{BLOCK_MATH_N}}
    Phase 3: 在已净化的文本中提取 $...$ → 替换为 {{INLINE_MATH_N}}
    """
    logger.info("[parser] 进入正则隔离器")
    text = state["draft_content"]

    # ===== Phase 0a: 提取标题 =====
    title = ""
    title_match = re.match(r'【标题】\s*(.+?)\s*\n', text)
    if title_match:
        title = title_match.group(1).strip()
        text = text[title_match.end():]
        logger.info(f"[parser] 提取标题: {title}")

    # ===== Phase 0b: 预处理修正错误标签 =====
    text = _sanitize_block_tags(text)

    formula_dict: dict[str, dict[str, str]] = {}
    inline_dict: dict[str, str] = {}
    figure_dict: dict[str, dict[str, str]] = {}

    # ===== Phase 1: 提取 Figure 标签 =====
    figure_matches = list(re.finditer(FIGURE_PATTERN, text, re.DOTALL))
    for idx, match in enumerate(reversed(figure_matches), start=1):
        label = match.group(1).strip()
        caption = match.group(2).strip()
        description = match.group(3).strip()
        placeholder = f"{FIGURE_PLACEHOLDER_PREFIX}{idx}{FIGURE_PLACEHOLDER_SUFFIX}"
        figure_dict[placeholder] = {
            "label": label,
            "caption": caption,
            "description": description,
        }
        text = text[:match.start()] + f"\n{placeholder}\n" + text[match.end():]
    if figure_dict:
        logger.info(f"[parser] 提取 Figure: {len(figure_dict)} 个")

    # ===== Phase 2: 提取 Block 公式 =====
    block_matches = list(re.finditer(BLOCK_MATH_PATTERN, text, re.DOTALL))

    # ===== Phase 2b: Fallback — 如果没有 <block_math> 标签，尝试提取 $$...$$ =====
    if not block_matches:
        logger.warning("[parser] 未找到 <block_math> 标签，启用 $$...$$ fallback 提取")
        fallback_matches = list(re.finditer(FALLBACK_BLOCK_PATTERN, text, re.DOTALL))
        for idx, match in enumerate(reversed(fallback_matches), start=1):
            content = match.group(1).strip()
            label = f"eq:auto_{idx}"
            placeholder = f"{BLOCK_PLACEHOLDER_PREFIX}{idx}{BLOCK_PLACEHOLDER_SUFFIX}"
            formula_dict[placeholder] = {"label": label, "content": content, "score": ""}
            text = text[:match.start()] + f"\n{placeholder}\n" + text[match.end():]
        logger.info(f"[parser] Fallback 提取 Block 公式: {len(formula_dict)} 个")
    else:
        for idx, match in enumerate(reversed(block_matches), start=1):
            label = match.group(1).strip()
            score = match.group(2) or ""
            content = match.group(3).strip()
            placeholder = f"{BLOCK_PLACEHOLDER_PREFIX}{idx}{BLOCK_PLACEHOLDER_SUFFIX}"
            formula_dict[placeholder] = {"label": label, "content": content, "score": score}
            text = text[:match.start()] + f"\n{placeholder}\n" + text[match.end():]

    # ===== Phase 3: 提取 Inline 公式（在 Block 已被移除的文本上操作） =====
    inline_matches = list(re.finditer(INLINE_MATH_PATTERN, text))
    for idx, match in enumerate(reversed(inline_matches), start=1):
        content = match.group(1).strip()
        placeholder = f"{INLINE_PLACEHOLDER_PREFIX}{idx}{INLINE_PLACEHOLDER_SUFFIX}"
        inline_dict[placeholder] = content
        text = text[:match.start()] + placeholder + text[match.end():]

    logger.info(
        f"[parser] 提取完成 | Figure: {len(figure_dict)} 个 | "
        f"Block 公式: {len(formula_dict)} 个 | "
        f"Inline 公式: {len(inline_dict)} 个"
    )

    result_dict = {
        "formula_dict": formula_dict,
        "inline_dict": inline_dict,
        "figure_dict": figure_dict,
        "tagged_text": text,
    }
    if title:
        result_dict["title"] = title
    return result_dict
