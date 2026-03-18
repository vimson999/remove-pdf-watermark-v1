#!/bin/bash
echo "🚀 正在启动 PDF 清洗平台 Web 后端..."
source venv/bin/activate
export FLASK_ENV=development
python run.py
