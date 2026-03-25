import sys
from pathlib import Path
import os

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.pdf_processor import PDFProcessor

def test_wipes():
    processor = PDFProcessor()
    samples = {
        "ms": "samples/摩根士丹利-中国新前沿：新型电力系统将推动中国电力设备资本支出增长-260320.pdf",
        "nomura": "samples/野村-比亚迪（1211.HK）发布刀片电池2.0，但可能还不够-260306.pdf"
    }
    
    output_dir = Path("samples/outputs/ms_nomura_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for key, path in samples.items():
        if os.path.exists(path):
            output_path = output_dir / f"cleaned_{key}.pdf"
            print(f"\n--- Testing specialized wipe for: {key} ---")
            success, msg = processor.remove_watermark(
                path, 
                str(output_path),
                mode='image_bleach',
                do_ocr=False # Speed up for testing
            )
            if success:
                print(f"SUCCESS: {output_path} generated.")
            else:
                print(f"FAILED: {msg}")

if __name__ == "__main__":
    test_wipes()
