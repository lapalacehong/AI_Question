"""
主题池加载器：从 topics.js 中解析 TOPIC_POOL 数组。
提供随机选题函数供 main.py 调用。
"""
import re
import random
from pathlib import Path
from config.settings import logger

# topics.js 与项目根目录同级
_TOPICS_JS_PATH = Path(__file__).resolve().parent.parent / "topics.js"


def _parse_topics_js(filepath: Path) -> list[str]:
    """从 JavaScript 文件中提取 TOPIC_POOL 字符串数组。"""
    if not filepath.exists():
        raise FileNotFoundError(f"主题文件未找到: {filepath}")

    text = filepath.read_text(encoding="utf-8")

    # 匹配所有双引号内的字符串（topics.js 中每个主题都是双引号包裹）
    topics = re.findall(r'"([^"]+)"', text)

    if not topics:
        raise ValueError(f"未能从 {filepath} 中解析到任何主题")

    logger.info(f"[topics] 从 topics.js 加载了 {len(topics)} 个主题")
    return topics


# 模块级缓存，仅解析一次
TOPIC_POOL: list[str] = _parse_topics_js(_TOPICS_JS_PATH)


def get_random_topic() -> str:
    """从主题池中随机选取一个主题。"""
    topic = random.choice(TOPIC_POOL)
    logger.info(f"[topics] 随机选取主题: {topic[:60]}...")
    return topic
