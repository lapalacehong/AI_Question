"""
全局工作流数据定义。
使用 TypedDict 确保类型安全。

WorkflowData 承载从输入规格化到最终产物的全部中间状态。
每个阶段仅写入自身负责的字段，不修改其他阶段的产物。

并行节点写冲突说明：
  math_verifier 仅写入 math_review，physics_verifier 仅写入 physics_review，
  structure_checker 仅写入 structure_review。三个并行节点写入不同的 key，无需锁。
"""
from typing import TypedDict


class WorkflowData(TypedDict):
    """状态机流转的全量数据容器。"""

    # ===== 输入与规划 =====
    mode: str                    # "topic_generation" | "literature_adaptation" | "idea_expansion" | "problem_enrichment"
    topic: str                   # 物理主题
    source_material: str         # 源材料（文献 / 原题 / 思路，自由命题时为空）
    difficulty: str              # 难度等级描述
    total_score: int             # 题目总分（20-80）
    difficulty_profile: dict     # 三维难度目标
    planning_notes: str          # 规划 Agent 输出的命题规划文本

    # ===== 生成产物 =====
    title: str                   # 命题 Agent 自拟的题目标题
    problem_text: str            # 题干 + 小问（命题生成 Agent 产出）
    solution_text: str           # 参考答案 + 评分点（解题生成 Agent 产出）
    draft_content: str           # problem_text + solution_text 合并文本（供审核使用）

    # ===== 审核 =====
    math_review: str             # 数学检查 Agent 意见
    physics_review: str          # 物理检查 Agent 意见
    structure_review: str        # 结构检查器意见

    # ===== 仲裁 =====
    arbiter_decision: str        # "PASS" | "RETRY_PROBLEM" | "RETRY_SOLUTION" | "ABORT"
    arbiter_feedback: str        # 仲裁给出的修改建议
    arbiter_reason: str          # 仲裁做出判决的理由摘要
    error_category: str          # "none" | "style" | "fatal"

    # ===== LaTeX 后处理 =====
    formula_dict: dict           # Block 公式字典
    inline_dict: dict            # Inline 公式字典
    figure_dict: dict            # Figure 字典
    tagged_text: str             # 占位符文本
    formatted_text: str          # 格式化 Agent 排版后文本（含占位符）
    final_latex: str             # 最终 LaTeX（公式已回填）
    template_report: str         # 模板修正报告
    figure_descriptions: dict    # 图片绘制需求

    # ===== 外部审题 =====
    external_feedback: str       # AI_Reviewer 返回的审题反馈
    external_decision: str       # "accepted" | "needs_revision" | "rejected" | ""

    # ===== 元数据（分阶段重试计数） =====
    # 三个计数器均由仲裁 Agent 在做出裁决后统一写入；命题 / 解题 Agent 不修改。
    # 首轮生成不计 retry：仅当仲裁返回 RETRY_PROBLEM / RETRY_SOLUTION 时对应阶段 +1。
    retry_count: int             # = problem_retry_count + solution_retry_count（展示用）
    problem_retry_count: int     # 命题阶段被要求重新生成的次数
    solution_retry_count: int    # 解题阶段被要求重新生成的次数
