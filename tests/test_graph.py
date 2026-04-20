"""
端到端集成测试（使用 Mock LLM，不消耗真实 API）。
运行: uv run pytest tests/test_graph.py -v

注意：测试已迁移至 test_state_machine.py。
本文件保留仅为向后兼容，避免 CI 中已有的 test_graph.py 引用失效。
"""
import importlib
import sys
from pathlib import Path

# 确保 tests/ 目录在 sys.path 中
_tests_dir = str(Path(__file__).parent)
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)

_mod = importlib.import_module("test_state_machine")

# 将所有测试类和函数注入当前模块命名空间
for _name in dir(_mod):
    if _name.startswith("Test") or _name.startswith("test_"):
        globals()[_name] = getattr(_mod, _name)
