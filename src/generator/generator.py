"""
命题 Agent。
- retry_count == 0: 根据 topic + difficulty 全新生成。
- retry_count > 0:  根据 arbiter_feedback 针对性修改，同时清空上轮 review。

支持三种生成模式（generation_mode）：
- "free": 自由命题（默认）
- "reference": 基于参考资料命题
- "adapt": 基于已有题目改编
"""
import re
import time

from model.state import AgentState
from model.stats import record
from client import get_client, stream_chat
from config.settings import (
    BIG_MODEL_NAME, BIG_MODEL_TEMPERATURE, BIG_MODEL_MAX_TOKENS, logger,
)
from prompts import load


# ============ 难度分级 ============

_FUSAI_KEYWORDS = ("复赛", "省赛", "省级", "预赛")
_JIXUNDUI_KEYWORDS = ("集训", "国家队", "CMO", "IMO", "国赛", "IPhO", "APhO")


def _difficulty_tier(difficulty: str) -> str:
    """
    将自由格式的中文难度字符串映射到三个竞赛等级。
    返回 "fusai" | "juesai" | "jixundui"，默认 "juesai"。
    """
    d = difficulty.strip()
    if any(k in d for k in _FUSAI_KEYWORDS):
        return "fusai"
    if any(k in d for k in _JIXUNDUI_KEYWORDS):
        return "jixundui"
    return "juesai"


def _build_system_prompt(tier: str, total_score: int) -> str:
    """组合通用排版规范 + 竞赛等级专属内容规则。"""
    base = load("generator", "system_prompt_base")
    content = load("generator", f"system_prompt_content_{tier}",
                   total_score=str(total_score))
    return base + "\n\n" + content


# ============ 分数段选择 ============

def _score_tier(total_score: int) -> str:
    """根据总分选择对应的分数段命题规模引导 key。"""
    if total_score < 40:
        return "score_guidance_low"
    elif total_score <= 60:
        return "score_guidance_mid"
    else:
        return "score_guidance_high"


# ============ 命题节点 ============

def generator_agent(state: AgentState) -> dict:
    """命题节点：调用大模型生成或修改物理竞赛题。"""
    retry = state.get("retry_count", 0)
    logger.info(f"[generator] 进入命题节点 | retry_count={retry}")

    client = get_client()
    total_score = state["total_score"]

    # 计算难度等级
    tier = state.get("difficulty_tier") or _difficulty_tier(state["difficulty"])

    # 构建 score_guidance + topic_scope
    score_guidance = load("generator", _score_tier(total_score),
                          total_score=str(total_score))
    topic_scope = load("generator", f"topic_scope_{tier}")

    # 构建系统提示词
    system_prompt = _build_system_prompt(tier, total_score)

    # 选择 user prompt 变体
    mode = state.get("generation_mode", "free")

    if retry == 0:
        if mode == "reference":
            user_prompt = load("generator", "user_prompt_with_reference",
                               topic=state["topic"], difficulty=state["difficulty"],
                               total_score=str(total_score),
                               score_guidance=score_guidance,
                               topic_scope=topic_scope,
                               reference_content=state.get("reference_content", ""),
                               reference_source=state.get("reference_source", ""))
        elif mode == "adapt":
            user_prompt = load("generator", "user_prompt_adapt",
                               difficulty=state["difficulty"],
                               total_score=str(total_score),
                               score_guidance=score_guidance,
                               topic_scope=topic_scope,
                               reference_content=state.get("reference_content", ""))
        else:
            user_prompt = load("generator", "user_prompt_initial",
                               topic=state["topic"], difficulty=state["difficulty"],
                               total_score=str(total_score),
                               score_guidance=score_guidance,
                               topic_scope=topic_scope)
    else:
        # 重试模式
        if state.get("reference_content"):
            user_prompt = load("generator", "user_prompt_retry_with_reference",
                               arbiter_feedback=state["arbiter_feedback"],
                               draft_content=state["draft_content"],
                               reference_content=state["reference_content"])
        else:
            user_prompt = load("generator", "user_prompt_retry",
                               arbiter_feedback=state["arbiter_feedback"],
                               draft_content=state["draft_content"])

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    logger.info(f"[generator] 难度等级={tier} | 生成模式={mode} | 正在等待 thinking model 思考...")
    t0 = time.time()
    content, usage = stream_chat(
        client,
        model=BIG_MODEL_NAME,
        messages=messages,
        temperature=BIG_MODEL_TEMPERATURE,
        max_tokens=BIG_MODEL_MAX_TOKENS,
    )
    elapsed = time.time() - t0
    logger.info(
        f"[generator] 命题模型返回 | {len(content)} 字符 | {elapsed:.0f}s | "
        f"tokens: {usage.prompt_tokens}+{usage.completion_tokens}={usage.total_tokens}"
    )

    # ===== 思维链过滤（兼容 thinking model 如 Gemini 3.1 Pro） =====
    for marker in ["【题干】", "【题干】："]:
        idx = content.find(marker)
        if idx > 0:
            logger.info(f"[generator] 检测到思维链前缀，从 '{marker}' 处截取正式内容")
            content = content[idx:]
            break

    if re.search(r'\b(Wait|Let\'s check|Hmm|Actually|OK so)\b', content[:200]):
        logger.warning("[generator] 输出疑似包含思维链碎片，尝试提取结构化部分")
        last_idx = content.rfind("【题干】")
        if last_idx >= 0:
            content = content[last_idx:]

    logger.info(f"[generator] 命题完成 | 输出长度={len(content)} 字符")

    record(
        f"generator_r{retry}", len(content), elapsed,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
    )

    return {
        "draft_content": content,
        "difficulty_tier": tier,
        "math_review": "",
        "physics_review": "",
    }
