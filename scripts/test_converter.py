import sys
import os

# 将项目根目录添加到 python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.document_converter import DocumentConverter

def test_conversion():
    input_file = "test.docx"
    output_file = "test.pdf"
    
    # 确保利好.docx 存在
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    try:
        print(f"Starting conversion: {input_file} -> {output_file}")
        result = DocumentConverter.docx_to_pdf(input_file, output_file)
        print(f"Successfully converted to: {result}")
        if os.path.exists(output_file):
            print(f"File size: {os.path.getsize(output_file)} bytes")
    except Exception as e:
        print(f"Conversion failed: {e}")

if __name__ == "__main__":
    test_conversion()
