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

input_file = "野村证券-亚洲洞察：霍尔木兹海峡在中国能源供应中的角色-260303_副本.pdf"
output_file = "野村证券-亚洲洞察_Parallel_Cleaned.pdf"

print(f"--- STARTING PARALLEL PROCESSING ON NOMURA REPORT ---")
processor = PDFProcessor(threshold=195)
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
