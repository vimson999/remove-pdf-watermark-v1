import sys
import os
from pathlib import Path
import json

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.pdf_analyzer import PDFAnalyzer

def test_samples():
    sample_dir = Path("samples")
    pdf_files = list(sample_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF samples found in samples/ directory.")
        return

    print(f"--- Analyzing {len(pdf_files)} PDF samples ---\n")

    for pdf in pdf_files:
        print(f"Processing: {pdf.name}...")
        report = PDFAnalyzer.analyze(str(pdf))
        
        # 简单打印核心安全指标
        sec = report.get("security", {})
        perms = sec.get("permissions_decoded", {})
        
        print(f"  [Security] Encrypted: {sec.get('is_encrypted')}, Info: {sec.get('encryption_info')}")
        print(f"  [Permissions] Print: {perms.get('print_high_res')}, Copy: {perms.get('copy_contents')}, Modify: {perms.get('modify_contents')}")
        
        # 保存详细报告到 logs 供查阅
        output_path = Path("logs") / f"{pdf.stem}_analysis.json"
        os.makedirs("logs", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        
        print(f"  [Report] Saved to {output_path}\n")

if __name__ == "__main__":
    test_samples()
