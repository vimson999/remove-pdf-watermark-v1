# PDF 智能去水印平台 (PDF-Watermark-Bleacher)

[![Version](https://img.shields.io/badge/version-v3.1-blue.svg)](https://github.com/v9/pytest)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 🎯 项目愿景
构建一个具备“视觉漂白”与“语义重构”双重能力的工业级 PDF 清洗平台，解决企业研报、扫描件中的复合水印难题。支持 Apple Silicon (M1/M2) 硬件加速。

---

## 🚩 快速启动指南 (Quick Start)

项目已集成 Git 版本控制，请确保在根目录下执行以下操作：

### 1. 环境准备 (Environment)
建议使用 Python 3.12+ 虚拟环境：
```bash
# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖项 (包含 EasyOCR, PyMuPDF, OpenCV 等)
pip install -r requirements.txt
```

### 2. 启动核心服务 (Services)
请按顺序启动以下三个终端窗口：

*   **窗口 A: 消息代理 (Redis)**
    ```bash
    redis-server
    ```
*   **窗口 B: 异步任务处理 (Celery Worker)**
    ```bash
    # 确保已激活 venv
    celery -A run.celery worker --loglevel=info
    ```
*   **窗口 C: Web 服务器 (Flask)**
    ```bash
    # 确保已激活 venv
    python run.py
    ```

### 3. 浏览器访问 (Browser Access)
服务启动后，在浏览器中输入以下地址即可进入控制面板：
👉 **[http://127.0.0.1:5005](http://127.0.0.1:5005)**

---

## 🚀 核心技术架构 (Architecture)

*   **混合引擎**：`PyMuPDF` (文本层清理) + `OpenCV` (图像层漂白)。
*   **语义重构**：集成 `EasyOCR`，通过 **MPS (Metal Performance Shaders)** 硬件加速实现在图片上方原位注入隐形文字层。
*   **异步调度**：`Celery` + `Redis` 实现大文件处理不阻塞，支持多进程并行清洗。
*   **智能分析**：自动识别扫描件/电子版，并推荐最优处理阈值。

---

## 🛠️ 硬件加速说明 (MPS Acceleration)
本平台针对 **Apple Silicon (M1/M2/M3)** 进行了深度优化：
*   OCR 推理默认开启 `mps` 加速，性能较 CPU 提升约 3-5 倍。
*   多进程模式下，每个进程均会尝试调用 GPU 资源。

---

## 📅 研发日志与状态
*   详细研发计划请参考：[GEMINI.md](./GEMINI.md)
*   每日交接记录请参考：[HANDOVER_LOG.md](./HANDOVER_LOG.md)
*   当前项目状态请参考：[PROJECT_STATUS.md](./PROJECT_STATUS.md)

---
&copy; 2026 Enterprise PDF Platform R&D Team.
