# PDF 智能去水印平台 - 研发路线图 (GEMINI.md)

> **项目状态**：已受 Git 版本控制管理。
> **当前版本**：v3.1 (Milestone 4 推进中)

## 🎯 项目愿景
构建一个具备“视觉漂白”与“语义重构”双重能力的工业级 PDF 清洗平台，解决企业研报、扫描件中的复合水印难题。

---

## 🚩 里程碑规划 (Milestones)

... (保持之前的 Milestone 内容不变) ...

---

## 🛡️ 研发纪律 (Development Discipline)

为了确保项目的高度透明与可持续性，所有参与者（包括 AI 助手）必须严格遵守以下纪律：

1.  **每日进度同步**：在每日工作结束前，必须更新 `HANDOVER_LOG.md`，涵盖：
    *   ✅ **今日完成工作**：量化、具体的成果描述。
    *   🛠️ **待完成/明天继续工作**：清晰的任务列表。
2.  **项目状态维护**：重大功能上线或里程碑达成后，同步更新 `PROJECT_STATUS.md`，反映最新的技术架构和功能列表。
3.  **原子化提交**：遵循 Git 规范，确保每次代码变更逻辑清晰，并附带必要的文档更新。

---

## 🛠️ 技术运行环境
*   **Language**: Python 3.12+
*   **Web Server**: Flask 3.0+
*   **Task Broker**: Redis 5.0+
*   **Worker**: Celery 5.3+
*   **Core Engine**: PyMuPDF 1.22+ & OpenCV 4.8+
*   **AI Engine**: EasyOCR (PyTorch MPS Accelerated)

---

## 🚀 启动指南 (Detailed Startup Guide)

请按以下标准步骤操作，确保所有服务正常运行：

### 1. 激活环境
```bash
source venv/bin/activate
```

### 2. 启动消息代理 (终端 1)
```bash
redis-server
```

### 3. 启动后台 Worker (终端 2)
```bash
# 开启多进程模式处理任务
celery -A run.celery worker --loglevel=info
```

### 4. 启动 Web 应用 (终端 3)
```bash
# 默认端口 5000
python run.py
```

### 5. 浏览器访问
访问地址：**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

---
