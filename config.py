"""
学练测一体化能力提升系统 - 配置管理模块

管理LLM连接、流程参数等系统配置
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)


class SkillTrainerConfig:
    """学练测系统配置"""

    # LLM配置
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL")

    # 流程配置
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "3"))
    ASSESSMENT_CYCLE: str = os.getenv("ASSESSMENT_CYCLE", "weekly")  # 评估周期

    # 输出配置
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", str(Path(__file__).parent / "output"))

    # 默认岗位（未指定时使用）
    DEFAULT_POSITION: str = os.getenv("DEFAULT_POSITION", "Python后端开发工程师")

    @classmethod
    def validate(cls) -> bool:
        """验证必要配置是否已设置"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 或 OPENAI_API_KEY 未配置")

        if errors:
            print("⚠️ 配置警告:")
            for err in errors:
                print(f"  - {err}")
            return False
        return True


config = SkillTrainerConfig()
