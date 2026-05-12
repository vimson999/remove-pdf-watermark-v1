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

def run_full_cycle():
    input_pdf = "samples/野村-比亚迪（1211.HK）发布刀片电池2.0，但可能还不够-260306.pdf"
    cleaned_pdf = "samples/outputs/nomura_byd_cleaned_tmp.pdf"
    final_protected_pdf = "samples/outputs/nomura_byd_final_protected.pdf"
    
    watermark_text = "西湖有鱼快来吃"
    
    print(f"🚀 [STEP 1] Deep Cleaning: Removing original watermarks from Nomura report...")
    
    # 1. Use PDFProcessor for deep cleaning (Image Bleach mode)
    processor = PDFProcessor(threshold=195)
    success_clean, msg_clean = processor.remove_watermark(
        input_pdf, 
        cleaned_pdf, 
        mode='image_bleach',
        do_redaction=True,
        do_header_clean=True
    )
    
    if not success_clean:
        print(f"❌ Cleaning failed: {msg_clean}")
        return

    print(f"✅ Cleaning finished. Temp file: {cleaned_pdf}")
    print(f"🚀 [STEP 2] Injecting New Watermark & AES-256 Protection...")

    # 2. Use PDFProtector to add our own watermark and lock permissions
    success_protect, result_protect = PDFProtector.add_watermark_and_protect(
        cleaned_pdf,
        final_protected_pdf,
        watermark_text=watermark_text,
        owner_pw="SECURE_BYD_KEY_2026"
    )

    if success_protect:
        print(f"✅ Full cycle completed!")
        print(f"📄 Final Protected PDF: {final_protected_pdf}")
        print(f"🛡️ Protection: AES-256, No User PW, Permissions Locked.")
        
        # Cleanup temp file
        if os.path.exists(cleaned_pdf):
            os.remove(cleaned_pdf)
    else:
        print(f"❌ Protection failed: {result_protect}")

if __name__ == "__main__":
    run_full_cycle()
