# 项目状态梳理 (2026-03-17)

## 1. 项目核心定位
*   **目标**：构建企业级、高可用的 PDF 智能去水印 Web 平台。
*   **状态**：已进入 **v3.0 语义重构与硬件加速时代**。
*   **技术栈**：Python 3.12 + Flask + OpenCV + PyMuPDF + Celery + Redis + EasyOCR (MPS Accelerated)。

## 2. 已实现的重大功能
*   **[算法层] 混合清洗与语义重建**：
    *   **双引擎 OCR 架构 (Multi-Engine Support)**：新增 PaddleOCR 3.4.0 引擎，与 EasyOCR 形成“高精度 vs 极速”互补。
    *   **语义重构 (OCR Injection)**：在漂白后的图片 PDF 上方原位注入透明文字层（Render Mode 3），恢复文档的可搜索与划选能力。
    *   **坐标归一化**：统一多引擎坐标系，实现像素级文字对齐。
    *   **像素级漂白**：利用 OpenCV 阈值算法处理 200/300 DPI 渲染图。
*   **[性能层] 硬件级加速架构**：
    *   **Apple Silicon (M1) 优化**：EasyOCR 链路全线激活 **MPS (Metal Performance Shaders)**。
    *   **多进程并行 (Parallel Processing)**：引入 `ProcessPoolExecutor` 实现多页 PDF 同步处理。
    *   **DPI 智能降维**：默认 DPI 调优至 200，在不损画质的前提下，像素处理量降低 55%。
*   **[工程层] 工业级监控与异步**：
    *   **全链路耗时埋点**：新增 `🚀 [START]`, `📝 [PAGE]`, `🤖 [OCR]` 等细粒度性能日志，实现处理瓶颈的可观测性。
    *   **Celery 异步队列**：任务分发与进度轮询（JS 实时展示）。

## 3. 当前架构图
```text
[ 用户上传 PDF ] -> [ Flask Web ] -> [ Redis Broker ] -> [ Celery Worker ]
                                                               |
                                            [ PDFProcessor 引擎 (Parallel & MPS) ]
                                                               |
[ 异步状态返回 ] <- [ 进度轮询 & 日志审计 ] <---------------- [ 完成语义清洗 ]
```

## 4. 下一步任务 (Roadmap)
*   **v3.1 智能参数推荐**：利用 AI 自动识别 PDF 类型（扫描件 vs 电子版），自动匹配最佳阈值与模式。
*   **v3.2 UI 批量任务增强**：支持多文件并行上传与独立的实时进度条展示。
*   **v3.3 容器化与部署**：编写 Docker-compose 一键启动 Web, Redis, Worker 镜像。

---
&copy; 2026 Enterprise PDF Platform R&D Team.
