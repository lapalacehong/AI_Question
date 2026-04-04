"""
Node 2a: 数学验算 Agent（并行节点之一）。
仅写入 math_review 字段，与 physics_verifier 无写冲突。
"""
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from state.schema import AgentState
from config.settings import (
    BIG_MODEL_API_KEY, BIG_MODEL_BASE_URL, BIG_MODEL_NAME,
    BIG_MODEL_MAX_TOKENS, BIG_MODEL_TIMEOUT, logger,
)
from config.prompts import MATH_VERIFIER_SYSTEM_PROMPT, VERIFIER_USER_PROMPT


def math_verifier(state: AgentState) -> dict:
    """数学审核节点：验证解答中所有数学推导的正确性。"""
    logger.info("[math_verifier] 进入数学验算节点")

    llm = ChatOpenAI(
        api_key=BIG_MODEL_API_KEY,
        base_url=BIG_MODEL_BASE_URL,
        model=BIG_MODEL_NAME,
        temperature=0.0,
        max_tokens=BIG_MODEL_MAX_TOKENS,
        timeout=BIG_MODEL_TIMEOUT,
        max_retries=3,
        streaming=True,
    )

    messages = [
        SystemMessage(content=MATH_VERIFIER_SYSTEM_PROMPT),
        HumanMessage(content=VERIFIER_USER_PROMPT.format(
            draft_content=state["draft_content"],
        )),
    ]

    logger.info("[math_verifier] 正在等待 thinking model 审核...")
    t0 = time.time()
    resp = llm.invoke(messages)
    content = resp.content
    elapsed = time.time() - t0
    logger.info(f"[math_verifier] 数学审核完成 | {len(content)} 字符 | {elapsed:.0f}s")

    from utils.run_stats import record
    record("math_verifier", len(content), elapsed)

    return {"math_review": content}
