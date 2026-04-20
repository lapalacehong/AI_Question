"""
AI_Reviewer 调用封装。
调用 ai-reviewer local 审题，读取报告文件。
"""
import json
import subprocess
from pathlib import Path

from model.state import WorkflowData
from config.config import logger, OUTPUT_DIR


def run_ai_reviewer(data: WorkflowData) -> dict:
    """
    调用 AI_Reviewer local 审核 final_latex。

    流程:
    1. 将 final_latex 写入临时 .tex 文件
    2. 调用 ai-reviewer local <file.tex>
    3. 读取生成的 JSON 报告
    4. 返回报告内容

    若 AI_Reviewer 未安装或调用失败，返回空报告并记录警告。
    """
    latex = data.get("final_latex", "")
    if not latex:
        logger.warning("[ai_reviewer] final_latex 为空，跳过外部审题")
        return {}

    # 写入临时文件
    tex_path = OUTPUT_DIR / "_review_temp.tex"
    tex_path.write_text(latex, encoding="utf-8")

    try:
        result = subprocess.run(
            ["ai-reviewer", "local", str(tex_path), "-o", str(OUTPUT_DIR)],
            capture_output=True, text=True, timeout=300,
        )

        if result.returncode != 0:
            logger.warning("[ai_reviewer] 审题进程返回非零: %d\nstderr: %s",
                           result.returncode, result.stderr[:500])
            return {"review_output": result.stdout, "review_error": result.stderr}

        # 查找 JSON 报告
        json_files = sorted(OUTPUT_DIR.glob("_review_temp*.json"), reverse=True)
        if json_files:
            report = json.loads(json_files[0].read_text(encoding="utf-8"))
            logger.info("[ai_reviewer] 审题报告加载成功: %s", json_files[0].name)
            return report

        logger.warning("[ai_reviewer] 未找到 JSON 审题报告")
        return {"review_output": result.stdout}

    except FileNotFoundError:
        logger.warning("[ai_reviewer] ai-reviewer 命令未找到，跳过外部审题")
        return {}
    except subprocess.TimeoutExpired:
        logger.warning("[ai_reviewer] 审题超时(300s)，跳过")
        return {}
    except Exception as e:
        logger.error("[ai_reviewer] 调用异常: %s", e)
        return {}
    finally:
        if tex_path.exists():
            tex_path.unlink(missing_ok=True)
