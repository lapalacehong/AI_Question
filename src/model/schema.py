"""
结构化输出模型定义。
"""
from pydantic import BaseModel, Field


class ArbiterDecision(BaseModel):
    """仲裁结构化输出模型。通过 Function Calling 强制 LLM 输出此格式。"""
    decision: str = Field(
        description="必须严格输出 'PASS', 'RETRY', 或 'ABORT' 三者之一"
    )
    reason: str = Field(
        description="做出该裁决的核心理由，简明扼要概括关键问题或通过原因（1-3句话）"
    )
    feedback: str = Field(
        description="综合评审意见及修改指导；若 PASS 则写'无需修改'"
    )
