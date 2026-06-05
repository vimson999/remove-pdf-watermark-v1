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
当前 Web 批量清洗和音频裁剪任务由 Flask 后台线程执行，并通过本地 SQLite 记录进度。日常使用只需要启动 Web 服务：

```bash
# 确保已激活 venv
python run.py
```

Celery/Redis 相关文件仍保留在项目中，作为后续迁移到独立异步任务队列的基础。

### 3. 浏览器访问 (Browser Access)
服务启动后，在浏览器中输入以下地址即可进入控制面板：
👉 **[http://127.0.0.1:5005](http://127.0.0.1:5005)**

---

## 🚀 核心技术架构 (Architecture)

*   **混合引擎**：`PyMuPDF` (文本层清理) + `OpenCV` (图像层漂白)。
*   **语义重构**：集成 `EasyOCR`，通过 **MPS (Metal Performance Shaders)** 硬件加速实现在图片上方原位注入隐形文字层。
*   **批量任务**：Web 端提交任务后由后台线程处理，SQLite 记录任务和逐文件进度。
*   **智能分析**：自动识别扫描件/电子版，并推荐最优处理阈值。

---

## 📁 本地工作目录约定 (Workspace)

这些目录用于本地处理数据，不进入 Git 仓库：

*   `待清理/`：放入待批量清洗的 PDF。
*   `清理完毕/`：批量清洗输出目录，保留输入目录的相对层级。
*   `音频/待清理/`：放入待裁剪音频。
*   `音频/清理完毕/`：音频裁剪输出目录。
*   `logs/`、`downloads/`、`uploads/`：运行日志、临时上传和下载产物。

仓库内应主要保留代码、模板、固定水印资源、少量可复现测试样本和测试用例。

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
