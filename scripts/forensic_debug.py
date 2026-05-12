import fitz
import sys
import json
from pathlib import Path

def forensic_scan(file_path):
    print(f"--- Forensic Scan: {file_path} ---\n")
    try:
        doc = fitz.open(file_path)
        
        # 1. 核心加密标记
        is_encrypted = doc.is_encrypted
        
        # 2. 权限位 (这是瑞银最常用的防线)
        perm_mask = doc.permissions
        
        # 3. 元数据加密指纹
        meta = doc.metadata or {}
        enc_info = meta.get("encryption", "N/A")
        
        # 4. 尝试身份认证 (如果失败说明存在所有者密码)
        auth_status = doc.authenticate("") # 尝试空密码

        # 5. 可复制性物理验证 (尝试物理提取第一页前 100 字符)
        try:
            text_preview = doc[0].get_text()[:100]
            can_physically_extract = len(text_preview.strip()) > 0
        except:
            can_physically_extract = False

        results = {
            "is_encrypted_flag": is_encrypted,
            "permissions_raw": perm_mask,
            "encryption_metadata": enc_info,
            "authentication_with_empty_pass": auth_status,
            "physical_extraction_test": can_physically_extract,
            "pdf_version": meta.get("format", "Unknown"),
            "is_linearized": getattr(doc, "is_linearized", "Unknown")
        }
        
        print(json.dumps(results, indent=4, ensure_ascii=False))
        doc.close()
    except Exception as e:
        print(f"Scan failed: {e}")

if __name__ == "__main__":
    target = "瑞银-全球贵金属评论：黄金仍是避险资产吗？-260317.pdf"
    forensic_scan(target)
