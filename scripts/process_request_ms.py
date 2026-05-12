import os
import sys
import logging

# 将项目根目录添加到路径中
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))

from app.services.pdf_processor import PDFProcessor

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process():
    input_pdf = "摩根士丹利-比亚迪股份（1211.HK）：澳大利亚见闻录-260409.pdf"
    output_pdf = "摩根士丹利-比亚迪股份（1211.HK）：澳大利亚见闻录-260409_cleaned.pdf"
    
    if not os.path.exists(input_pdf):
        print(f"❌ 找不到文件: {input_pdf}")
        return

    print(f"🚀 开始处理: {input_pdf}")
    
    # 初始化处理器，默认阈值 195 (analyze_pdf 会自动调整)
    processor = PDFProcessor()
    
    # 移除水印
    # mode='image_bleach' 使用图像漂白模式，能有效去除大摩这类机构的背景水印
    success, msg = processor.remove_watermark(
        input_pdf, 
        output_pdf, 
        mode='image_bleach',
        do_redaction=True,  # 擦除已知的文本水印
        do_header_clean=True, # 清理页眉
        do_ocr=False # 如果检测到原生文字层，通常不需要 OCR，提高速度
    )
    
    if success:
        print(f"✅ 处理成功！输出文件: {output_pdf}")
    else:
        print(f"❌ 处理失败: {msg}")

if __name__ == "__main__":
    process()
