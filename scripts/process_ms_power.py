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

def process_ms_report():
    input_pdf = "samples/摩根士丹利-中国新前沿：新型电力系统将推动中国电力设备资本支出增长-260320.pdf"
    cleaned_tmp = "samples/outputs/ms_power_cleaned_tmp.pdf"
    final_pdf = "samples/outputs/MS_Power_Grid_2026_Protected.pdf"
    
    watermark_text = "西湖有鱼快来吃"
    
    print(f"🚀 [MS-START] Processing Morgan Stanley Report: {os.path.basename(input_pdf)}")
    
    # 1. Deep Cleaning with current Strategy Group (Threshold 245 + Header Clean + Footer Wipe)
    processor = PDFProcessor(threshold=245)
    success_clean, msg_clean = processor.remove_watermark(
        input_pdf, 
        cleaned_tmp, 
        mode='image_bleach',
        do_redaction=True,
        do_header_clean=True
    )
    
    if not success_clean:
        print(f"❌ [CLEAN FAILED] {msg_clean}")
        return

    print(f"✅ [CLEAN SUCCESS] Strategy Group applied (Global Bleach + Footer Wipe).")
    print(f"🚀 [PROTECT-START] Injecting New Watermark & AES-256...")

    # 2. Add New Watermark and Lock Permissions
    success_protect, result_protect = PDFProtector.add_watermark_and_protect(
        cleaned_tmp,
        final_pdf,
        watermark_text=watermark_text,
        owner_pw="SECURE_MS_2026"
    )

    if success_protect:
        print(f"✅ [ALL SUCCESS] Full lifecycle completed!")
        print(f"📄 Protected Result: {final_pdf}")
        print(f"🛡️ Strategy: Extreme Bleach + MS-Specific Cleaning + New Watermark + Permission Lock.")
        
        # Cleanup
        if os.path.exists(cleaned_tmp):
            os.remove(cleaned_tmp)
    else:
        print(f"❌ [PROTECT FAILED] {result_protect}")

if __name__ == "__main__":
    process_ms_report()
