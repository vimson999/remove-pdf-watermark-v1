# 项目状态梳理 (2026-03-18)

## 1. 项目核心定位
*   **目标**：构建企业级、高可用的 PDF 智能去水印 Web 平台。
*   **当前版本**：**v3.5 (专家重构版)**
*   **技术栈**：Python 3.12 + Flask + OpenCV + PyMuPDF + Celery + Redis + EasyOCR (MPS) + PaddleOCR (Adaptive)。

## 2. 已实现的重大功能 (里程碑核心)
*   **[架构层] 多引擎策略工厂 (Multi-Engine Factory)**：
    *   **动态切换**：支持 EasyOCR (极速/GPU) 与 PaddleOCR (高精度/CPU) 的无缝热切换。
    *   **单例管理**：实现进程级 Reader 单例，优化资源占用与冷启动性能。
*   **[算法层] 混合清洗与 DPI 自适应**：
    *   **DPI 智能降级**：自动识别“像素巨兽”文档并动态调整采样率，平衡处理速度与 OCR 精度。
    *   **语义重构 (OCR Injection)**：在漂白图上方原位注入透明文字层（Render Mode 3），恢复可划选/搜索能力。
    *   **原子化漂白**：自适应阈值算法，支持 UBS 蓝、灰度水印的精准剥离。
*   **[工程层] 工业级监控与 AI 闭环**：
    *   **智能仪表盘**：任务级引擎勋章标注、精准耗时回传、实时进度反馈。
    *   **AI 智能分析**：根据色彩空间自动推荐最优清洗参数并实现一键应用。

## 3. 当前架构图
```text
[ 用户上传 PDF ] -> [ Flask Web ] -> [ Redis Broker ] -> [ Celery Worker ]
                                                               |
                                            [ Strategy Factory (OCRProvider) ]
                                                               |
                                            [ Adaptive DPI Rendering Engine ]
                                                               |
[ 引擎详情勋章 ] <- [ 状态轮询 (Socket/Polling) ] <----------- [ 语义清洗完成 ]
```

## 4. 下一步待办 (Roadmap)
*   **v3.6 UI 统计增强**：显示识别对象总数，量化重构质量。
*   **v4.0 容器化部署**：Dockerfile 编写与 Redis/Worker 编排。
*   **v4.1 结构还原**：探索表格与段落逻辑的语义级恢复。

---
&copy; 2026 Enterprise PDF Platform R&D Team.
