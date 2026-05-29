import os
import sys
import logging
import time
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.pdf_processor import PDFProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("batch_process_0513.log")
    ]
)
logger = logging.getLogger(__name__)

def batch_process_folder(input_folder: str, output_folder: str):
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(input_path.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_folder}")
        return

    logger.info(f"🚀 Found {len(pdf_files)} PDFs in {input_folder}. Starting batch cleaning...")
    
    # Initialize processor
    # Using threshold 245 as per PROJECT_STATUS.md for high-intensity GS cleaning
    processor = PDFProcessor(threshold=245)
    
    stats = {
        "success": 0,
        "failed": 0,
        "total_time": 0
    }
    
    start_total = time.time()
    
    for pdf_file in pdf_files:
        filename = pdf_file.name
        out_file = output_path / f"Cleaned_{filename}"
        
        logger.info(f"--- Processing: {filename} ---")
        start_single = time.time()
        
        try:
            success, message = processor.remove_watermark(
                str(pdf_file),
                str(out_file),
                mode='image_bleach',
                do_redaction=True,
                do_header_clean=True,
                do_ocr=False # Disable OCR for speed in this test
            )
            
            duration = time.time() - start_single
            if success:
                logger.info(f"✅ Success: {filename} ({duration:.2f}s)")
                stats["success"] += 1
            else:
                logger.error(f"❌ Failed: {filename} - {message}")
                stats["failed"] += 1
                
        except Exception as e:
            logger.error(f"💥 Error processing {filename}: {str(e)}")
            stats["failed"] += 1
            
    total_duration = time.time() - start_total
    logger.info(f"\n" + "="*40)
    logger.info(f"🏁 Batch Processing Complete")
    logger.info(f"📂 Output folder: {output_folder}")
    logger.info(f"📊 Stats: {stats['success']} succeeded, {stats['failed']} failed")
    logger.info(f"⏱️ Total time: {total_duration:.2f}s")
    logger.info("="*40)

if __name__ == "__main__":
    batch_process_folder("0513", "0513_cleaned")
