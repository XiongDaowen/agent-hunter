#!/bin/bash
# agent-hunter 定时运行脚本
# 用法: 添加到 crontab 或 systemd timer

# 项目路径
PROJECT_DIR="/path/to/agent-hunter"
LOG_FILE="$PROJECT_DIR/logs/cron.log"
PYTHON="python3"

# 进入项目目录
cd "$PROJECT_DIR" || exit 1

# 运行主程序
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始运行 agent-hunter..." >> "$LOG_FILE"
$PYTHON run.py >> "$LOG_FILE" 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 运行完成" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
