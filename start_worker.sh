#!/bin/bash
echo "⚙️ 正在启动 Celery 异步处理 Worker..."
source venv/bin/activate
# 使用 info 级别日志以便观察清洗细节
celery -A run.celery worker --loglevel=info
