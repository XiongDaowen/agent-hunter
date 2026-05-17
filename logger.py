#!/usr/bin/env python3
"""日志模块 — 支持控制台和文件输出"""

import logging
import sys
from pathlib import Path

# 日志配置
LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "agent-hunter.log"

# 创建日志目录
LOG_DIR.mkdir(exist_ok=True)

# 创建 logger
logger = logging.getLogger("agent-hunter")
logger.setLevel(logging.DEBUG)

# 避免重复添加 handler
if not logger.handlers:
    # 控制台 handler（INFO 级别，带 emoji）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件 handler（DEBUG 级别，详细记录）
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)


# 便捷函数
def info(msg: str):
    """普通信息"""
    logger.info(msg)


def success(msg: str):
    """成功信息"""
    logger.info(f"✅ {msg}")


def warning(msg: str):
    """警告信息"""
    logger.warning(f"⚠ {msg}")


def error(msg: str):
    """错误信息"""
    logger.error(f"❌ {msg}")


def debug(msg: str):
    """调试信息（仅写入文件）"""
    logger.debug(msg)


def step(msg: str):
    """步骤信息"""
    logger.info(f"\n{'='*50}")
    logger.info(f"  {msg}")
    logger.info(f"{'='*50}")


def sub_step(msg: str):
    """子步骤信息"""
    logger.info(f"  → {msg}")
