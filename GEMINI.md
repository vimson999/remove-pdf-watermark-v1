# PDF 智能安全与处理平台 - 研发路线图 (GEMINI.md)

> **项目状态**：已受 Git 版本控制管理。
> **当前版本**：v4.0 (Milestone 5 启动中)

## 🎯 项目愿景
构建工业级 PDF 安全与结构化处理平台，提供“取证级解析”与“生产级处理”能力，涵盖：**深度解析、智能拆分、自主加密、极致解密、交互可视化** 五大核心模块。

---

## 🚩 里程碑规划 (Milestones)

### Milestone 4: 视觉重构与性能巅峰 (已达成)
- [x] **多引擎策略工厂**: 支持 EasyOCR/PaddleOCR 动态切换。
- [x] **DPI 自适应**: 解决超大 PDF 处理性能瓶颈。
- [x] **并发清洗**: 基于 Celery 的多进程并行处理。

### Milestone 5: PDF 安全工具箱 (当前阶段)
- [ ] **M5.1 深度解析引擎**: 实现加密算法识别（AES/RC4）、权限位透视与结构指纹分析。
- [ ] **M5.2 结构化处理**: 支持按物理页码及逻辑书签（Outlines）的无损拆分。
- [ ] **M5.3 自主加密**: 支持 AES-256 标准的所有者/用户密码设置与细粒度权限管控。
- [ ] **M5.4 可视化中心**: 仪表盘式安全分析界面与拖拽拆分交互。

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
访问地址：**[http://127.0.0.1:5005](http://127.0.0.1:5005)**

---

---
