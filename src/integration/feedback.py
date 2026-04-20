"""
AI_Reviewer 审题反馈适配器。
将 AI_Reviewer 的 JSON 报告转换为 WorkflowData 可消费的反馈格式。
"""
from model.state import WorkflowData
from config.config import logger


def adapt_feedback(data: WorkflowData, review_result: dict) -> dict:
    """
    将 AI_Reviewer JSON 报告转为 WorkflowData 字段。

    判定逻辑：
    - 综合难度偏差 ≤ 2 且无严重错误 → accepted
    - 存在可修复问题 → needs_revision
    - 严重物理 / 数学错误 → rejected
    """
    if not review_result:
        logger.info("[feedback] 无外部审题结果，默认 accepted")
        return {"external_feedback": "", "external_decision": "accepted"}

    # 从报告中提取关键字段
    summary = review_result.get("summary", "")
    difficulty = review_result.get("difficulty", {})
    node_reviews = review_result.get("node_reviews", [])

    # 统计严重错误
    critical_errors = 0
    for node in node_reviews:
        correctness = node.get("correctness", "")
        if isinstance(correctness, str) and "incorrect" in correctness.lower():
            critical_errors += 1

    # 构建反馈文本
    feedback_parts = []
    if summary:
        feedback_parts.append(f"综合评估: {summary}")
    if difficulty:
        comp = difficulty.get("computation_difficulty", "N/A")
        think = difficulty.get("thinking_difficulty", "N/A")
        overall = difficulty.get("overall_difficulty", "N/A")
        feedback_parts.append(f"难度评价: 计算={comp}, 思维={think}, 综合={overall}")
    if critical_errors:
        feedback_parts.append(f"发现 {critical_errors} 个严重错误")

    feedback_text = "\n".join(feedback_parts)

    # 判定
    if critical_errors >= 2:
        decision = "rejected"
    elif critical_errors >= 1:
        decision = "needs_revision"
    else:
        decision = "accepted"

    logger.info("[feedback] 外部审题判定: %s | 严重错误: %d", decision, critical_errors)
    return {"external_feedback": feedback_text, "external_decision": decision}
