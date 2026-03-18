import sys
import logging
import os
import time
from app.services.pdf_processor import PDFProcessor

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

def progress(msg, percent):
    if percent % 10 == 0:
        print(f"📊 [UI PROGRESS] {percent}% - {msg}", flush=True)

def main():
    input_file = "瑞银-中国中免（601888）我们仍看好公司增长前景.pdf"
    output_file = "瑞银-中国中免_Parallel_M1_Accelerated.pdf"

    print(f"--- STARTING PARALLEL PROCESSING ON UBS REPORT (M1 ACCELERATED) ---")
    processor = PDFProcessor(threshold=180) 
    success, msg = processor.remove_watermark(
        input_path=input_file,
        output_path=output_file,
        mode='image_bleach',
        do_ocr=True,
        do_redaction=True,
        do_header_clean=True,
        progress_callback=progress
    )

    if success:
        print(f"\n--- PROCESSING FINISHED SUCCESSFULLY ---")
        print(f"File saved to: {output_file}")
        size = os.path.getsize(output_file)
        print(f"Output file size: {size / (1024*1024):.2f} MB")
    else:
        print(f"\n--- PROCESSING FAILED: {msg} ---")

if __name__ == '__main__':
    main()
