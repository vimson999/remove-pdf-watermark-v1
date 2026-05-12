import fitz
import os
from pathlib import Path
import sys
import json

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))
from app.services.pdf_analyzer import PDFAnalyzer

def create_and_test():
    output_path = "samples/encrypted_test_complex.pdf"
    
    # 1. 创建一个简单的 PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "This is a restricted PDF for testing complex permissions.")
    
    # 2. 设置权限与加密
    # 权限位设置：允许低清打印 (PRINT) 和 辅助提取 (ACCESSIBILITY)
    # 禁止复制、禁止修改、禁止高清打印
    perm = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_ACCESSIBILITY
    
    doc.save(output_path, 
             encryption=fitz.PDF_ENCRYPT_AES_256, 
             owner_pw="admin", 
             user_pw="guest",
             permissions=perm)
    doc.close()
    
    print(f"Created encrypted test file: {output_path}")
    
    # 3. 测试 1: 未认证解析
    print("\n--- Test 1: Analysis WITHOUT Password ---")
    report_locked = PDFAnalyzer.analyze(output_path)
    print(f"Authenticated: {report_locked['security']['authenticated']}")
    print(f"Permissions Decoded (Copy): {report_locked['security']['permissions_decoded']['copy_contents']}")

    # 4. 测试 2: 持证解析 (使用正确密码)
    print("\n--- Test 2: Analysis WITH Password ('guest') ---")
    report_auth = PDFAnalyzer.analyze(output_path, password="guest")
    print(f"Authenticated: {report_auth['security']['authenticated']}")
    print(f"Permissions Decoded:")
    print(json.dumps(report_auth['security']['permissions_decoded'], indent=4))
    print(f"Verification Results: {report_auth['verification']}")

    # 5. 清理
    if os.path.exists(output_path):
        os.remove(output_path)

if __name__ == "__main__":
    create_and_test()
