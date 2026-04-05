"""
回填器（纯 Python，不调用任何 LLM）。
将 formatted_text 中的占位符替换回原始数学公式，使用 CPHOS 模板命令。
"""
import re

from model.state import AgentState
from config.settings import logger


def python_merger(state: AgentState) -> dict:
    """
    回填器（CPHOS 模板对齐）：
    1. 按文档顺序收集占位符，建立 label → 公式编号映射
    2. 回填 Block 公式（\\eqtagscore / \\eqtag + \\label{eq:N}）
    3. 回填 Figure 占位符 → figure 环境
    4. 回填 Inline 公式
    5. 交叉引用重映射（\\ref{旧label} → \\ref{eq:N} / \\ref{fig:N}）
    6. 题干小问 → \\subq{N}\\label{q:N}
    7. 解答小问 → \\solsubq{N}{score}
    8. 添加 \\scoring 命令
    9. 计算总分填入 \\begin{problem}[总分]
    """
    logger.info("[merger] 进入回填器")
    result = state["formatted_text"]
    formula_dict = state.get("formula_dict", {})
    inline_dict = state.get("inline_dict", {})
    figure_dict = state.get("figure_dict", {})

    # ===== Step 1: 按文档出现顺序收集占位符 =====
    block_order = re.findall(r'\{\{BLOCK_MATH_\d+\}\}', result)
    fig_order = re.findall(r'\{\{FIGURE_\d+\}\}', result)

    # ===== Step 2: 构建 label → 编号 映射 =====
    label_to_eq: dict[str, int] = {}
    for eq_num, ph in enumerate(block_order, start=1):
        if ph in formula_dict:
            label_to_eq[formula_dict[ph]["label"]] = eq_num

    label_to_fig: dict[str, int] = {}
    for fig_num, ph in enumerate(fig_order, start=1):
        if ph in figure_dict:
            label_to_fig[figure_dict[ph]["label"]] = fig_num

    # ===== Step 3: 回填 Block 公式 → CPHOS equation 环境 =====
    for eq_num, ph in enumerate(block_order, start=1):
        if ph in formula_dict:
            data = formula_dict[ph]
            content = data["content"]
            score = data.get("score", "")
            content = re.sub(r'\\tag\{[^}]*\}\s*', '', content).strip()

            if score:
                eq_cmd = f"\\eqtagscore{{{eq_num}}}{{{score}}}"
            else:
                eq_cmd = f"\\eqtag{{{eq_num}}}"

            latex_block = (
                f"\n\\begin{{equation}}\n"
                f"    {content} {eq_cmd} \\label{{eq:{eq_num}}}\n"
                f"\\end{{equation}}\n"
            )
            result = result.replace(ph, latex_block, 1)

    # ===== Step 4: 回填 Figure → CPHOS figure 环境（占位图片） =====
    figure_descriptions: dict[str, dict[str, str]] = {}
    for fig_num, ph in enumerate(fig_order, start=1):
        if ph in figure_dict:
            data = figure_dict[ph]
            caption = data.get("caption", "")
            fig_block = (
                f"\n%\\begin{{figure}}[H]\n"
                f"%    \\centering\n"
                f"%    \\includegraphics[width=0.4\\textwidth]{{fig/fig_{fig_num}.pdf}}\n"
                f"%    \\caption{{{caption}}}\n"
                f"%    \\label{{fig:{fig_num}}}\n"
                f"%\\end{{figure}}\n"
            )
            result = result.replace(ph, fig_block, 1)
            figure_descriptions[f"fig_{fig_num}"] = {
                "filename": f"fig_{fig_num}.pdf",
                "caption": caption,
                "description": data.get("description", ""),
            }

    # ===== Step 5: 回填 Inline 公式 → 恢复 $...$ =====
    for placeholder, content in inline_dict.items():
        result = result.replace(placeholder, f"${content}$")

    # ===== Step 6: 交叉引用重映射 =====
    for label, num in label_to_eq.items():
        result = result.replace(f"\\ref{{{label}}}", f"\\ref{{eq:{num}}}")
        result = result.replace(f"\\eqref{{{label}}}", f"\\eqref{{eq:{num}}}")
    for label, num in label_to_fig.items():
        result = result.replace(f"\\ref{{{label}}}", f"\\ref{{fig:{num}}}")

    # ===== Step 7: 题干小问 → \subq{N}\label{q:N} =====
    stmt_start = result.find("\\begin{problemstatement}")
    stmt_end = result.find("\\end{problemstatement}")
    if stmt_start >= 0 and stmt_end > stmt_start:
        stmt = result[stmt_start:stmt_end]
        stmt = re.sub(
            r'\n\s*\((\d+)\)\s+',
            r'\n\n\\subq{\1}\\label{q:\1} ',
            stmt,
        )
        result = result[:stmt_start] + stmt + result[stmt_end:]

    # ===== Step 8: 解答小问 → \solsubq{N}{score} =====
    sol_start = result.find("\\begin{solution}")
    sol_end = result.find("\\end{solution}")
    if sol_start >= 0 and sol_end > sol_start:
        sol = result[sol_start:sol_end]
        sol = re.sub(
            r'\n\s*\((\d+)\)\s*\[(\d+)\u5206\]\s*',
            r'\n\n\\solsubq{\1}{\2}\n',
            sol,
        )
        result = result[:sol_start] + sol + result[sol_end:]

    # ===== Step 9: 添加 \scoring 命令 =====
    if '\\scoring' not in result and '\\end{solution}' in result:
        result = result.replace(
            '\\end{solution}',
            '\n\\scoring\n\\end{solution}',
        )

    # ===== Step 10: 计算总分并填入 \begin{problem}[总分] =====
    scores = re.findall(r'\\solsubq\{\d+\}\{(\d+)\}', result)
    if scores:
        total = sum(int(s) for s in scores)

        def _set_total(m):
            title = m.group(1) or ""
            return f"\\begin{{problem}}[{total}]{{{title}}}"

        result = re.sub(
            r'\\begin\{problem\}(?:\[\d*\])?\{([^}]*)\}',
            _set_total,
            result,
        )

    # ===== 校验 =====
    residual = []
    if "{{BLOCK_MATH_" in result:
        residual.append("BLOCK_MATH")
    if "{{INLINE_MATH_" in result:
        residual.append("INLINE_MATH")
    if "{{FIGURE_" in result:
        residual.append("FIGURE")
    if residual:
        logger.warning(f"[merger] 回填后仍存在残留占位符: {', '.join(residual)}")
    else:
        logger.info("[merger] 回填完成，无残留占位符")

    return {"final_latex": result, "figure_descriptions": figure_descriptions}
