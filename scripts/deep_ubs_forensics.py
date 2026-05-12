import sys
from pathlib import Path
import json

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.pdf_forensics import PDFForensics

def run_deep_scan(target_file):
    print(f"--- 🚨 DEEP FORENSIC SCAN START: {target_file} 🚨 ---\n")
    
    report = PDFForensics.deep_scan(target_file)
    
    # 打印发现汇总
    print(f"[Summary] Found {len(report.get('hidden_text_found', []))} pages with hidden text.")
    print(f"[Summary] Found {len(report.get('ocg_layers', []))} OCG layers.")
    print(f"[Summary] Found {len(report.get('processing_traces', []))} suspicious processing metadata objects.\n")

    # 打印具体的隐形文字内容 (Proof!)
    if report.get('hidden_text_found'):
        print("--- 🔬 Evidence: Hidden Text Found ---")
        for p_rep in report['hidden_text_found']:
            print(f"  Page {p_rep['page']}:")
            for f in p_rep['findings']:
                print(f"    Text: '{f['text']}' | Reason: {f['reason']} | Font: {f['font']}")

    # 打印隐藏图层名称 (Proof!)
    if report.get('ocg_layers'):
        print("\n--- 🔬 Evidence: OCG Layers Found ---")
        for layer in report['ocg_layers']:
            print(f"  XREF: {layer['xref']} | Layer Name: '{layer['name']}'")

    # 打印底层处理痕迹
    if report.get('processing_traces'):
        print("\n--- 🔬 Evidence: Metadata Trace (Software Fingerprints) ---")
        for trace in report['processing_traces']:
            print(f"  XREF: {trace['xref']} | Trace: {trace['content']}")

if __name__ == "__main__":
    target = "瑞银-全球贵金属评论：黄金仍是避险资产吗？-260317.pdf"
    if Path(target).exists():
        run_deep_scan(target)
    else:
        print(f"File not found: {target}")
