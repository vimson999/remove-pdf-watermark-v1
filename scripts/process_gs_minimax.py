import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pdf_processor import PDFProcessor
from app.services.pdf_protector import PDFProtector

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_gs_minimax():
    input_pdf = "samples/260303-GS-MiniMax集团（0100.HK）2025财年四季度业绩初评.pdf"
    cleaned_tmp = "samples/outputs/gs_minimax_cleaned_tmp.pdf"
    final_pdf = "samples/outputs/260303_GS_MiniMax_Protected.pdf"
    
    watermark_text = "西湖有鱼快来吃"
    
    print(f"🚀 [STEP 1] Deep Cleaning: Removing original GS watermarks and fingerprinting...")
    
    # 1. Use PDFProcessor for extreme cleaning (Threshold 245)
    processor = PDFProcessor(threshold=245)
    success_clean, msg_clean = processor.remove_watermark(
        input_pdf, 
        cleaned_tmp, 
        mode='image_bleach',
        do_redaction=True,
        do_header_clean=True
    )
    
    if not success_clean:
        print(f"❌ Cleaning failed: {msg_clean}")
        return

    print(f"✅ Cleaning finished. Temp file: {cleaned_tmp}")
    print(f"🚀 [STEP 2] Injecting New Watermark & AES-256 Protection...")

    # 2. Use PDFProtector to add our own watermark and lock permissions
    success_protect, result_protect = PDFProtector.add_watermark_and_protect(
        cleaned_tmp,
        final_pdf,
        watermark_text=watermark_text,
        owner_pw="SECURE_GS_KEY_2026"
    )

    if success_protect:
        print(f"✅ Full cycle completed!")
        print(f"📄 Final Protected PDF: {final_pdf}")
        print(f"🛡️ Protection: AES-256, No User PW, Permissions Locked.")
        
        # Cleanup temp file
        if os.path.exists(cleaned_tmp):
            os.remove(cleaned_tmp)
    else:
        print(f"❌ Protection failed: {result_protect}")

if __name__ == "__main__":
    process_gs_minimax()
