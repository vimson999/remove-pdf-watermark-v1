import os
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

def run_demo():
    # 1. Setup paths
    base_dir = Path("音频")
    output_base = Path("samples/outputs/demonstration")
    output_base.mkdir(parents=True, exist_ok=True)
    
    dates = ["20260301", "20260302", "20260303"]
    
    processor = PDFProcessor(threshold=195)
    protector = PDFProtector()
    
    target_files = []
    for d in dates:
        date_dir = base_dir / d
        if date_dir.exists():
            pdfs = list(date_dir.glob("*.pdf"))
            target_files.extend(pdfs)
    
    logger.info(f"Found {len(target_files)} PDFs to process.")
    
    results = []
    for pdf_path in target_files:
        filename = pdf_path.name
        temp_clean_path = output_base / f"temp_cleaned_{filename}"
        final_protected_path = output_base / filename
        
        logger.info(f"--- Processing: {filename} ---")
        
        # Step A: Clean (Remove old watermarks)
        # Note: Using image_bleach mode for high-fidelity cleaning
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
            
        # Step B: Protect (Add new dynamic watermark and AES-256)
        success_prot, owner_pw = protector.add_watermark_and_protect(
            str(temp_clean_path),
            str(final_protected_path),
            watermark_text="请您不要外传",
            owner_pw="gemini2026"
        )
        
        if success_prot:
            logger.info(f"Successfully processed and secured: {filename}")
            results.append(final_protected_path)
            # Cleanup temp file
            if temp_clean_path.exists():
                temp_clean_path.unlink()
        else:
            logger.error(f"Protection failed for {filename}: {owner_pw}")

    logger.info(f"\nBatch processing complete! {len(results)} files saved to {output_base}")

if __name__ == "__main__":
    run_demo()
