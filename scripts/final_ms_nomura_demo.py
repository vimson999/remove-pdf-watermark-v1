import sys
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.pdf_processor import PDFProcessor
from app.services.pdf_protector import PDFProtector

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_final_demo():
    output_dir = Path("samples/outputs/final_demo")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    samples = [
        "samples/摩根士丹利-中国新前沿：新型电力系统将推动中国电力设备资本支出增长-260320.pdf",
        "samples/野村-比亚迪（1211.HK）发布刀片电池2.0，但可能还不够-260306.pdf"
    ]
    
    processor = PDFProcessor()
    protector = PDFProtector()
    
    for path_str in samples:
        pdf_path = Path(path_str)
        if not pdf_path.exists():
            logger.error(f"File not found: {path_str}")
            continue
            
        filename = pdf_path.name
        temp_clean_path = output_dir / f"temp_cleaned_{filename}"
        final_protected_path = output_dir / f"Final_{filename}"
        
        logger.info(f"\n===== Processing: {filename} =====")
        
        # Step 1: Intelligent Cleaning (Auto-detects MS/Nomura)
        success_clean, msg_clean = processor.remove_watermark(
            str(pdf_path), 
            str(temp_clean_path),
            mode='image_bleach',
            do_header_clean=True,
            do_redaction=True
        )
        
        if not success_clean:
            logger.error(f"Clean failed for {filename}: {msg_clean}")
            continue
            
        # Step 2: V3 Adversarial Protection
        success_prot, owner_pw = protector.add_watermark_and_protect(
            str(temp_clean_path),
            str(final_protected_path),
            watermark_text="请您不要外传",
            owner_pw="final_test_2026"
        )
        
        if success_prot:
            logger.info(f"SUCCESS: Final protected file saved to {final_protected_path}")
            # Cleanup temp
            if temp_clean_path.exists():
                temp_clean_path.unlink()
        else:
            logger.error(f"Protection failed for {filename}: {owner_pw}")

if __name__ == "__main__":
    run_final_demo()
