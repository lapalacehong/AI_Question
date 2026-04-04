"""
运行时统计收集器 — 各节点写入耗时/字符数，main.py 结束时读取并写入 TEST_LOG.md。
"""

_stats: dict[str, dict] = {}


def record(node: str, chars: int, elapsed: float, extra: str = "") -> None:
    """记录一个节点的输出。"""
    _stats[node] = {"chars": chars, "elapsed": elapsed, "extra": extra}


def get_all() -> dict[str, dict]:
    return dict(_stats)


def clear() -> None:
    _stats.clear()
