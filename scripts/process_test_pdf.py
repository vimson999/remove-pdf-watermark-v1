import sys
import logging
import os
from app.services.pdf_processor import PDFProcessor

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

def progress(msg, percent):
    # Reduced progress output to avoid cluttering but keep milestones
    if percent % 10 == 0:
        print(f"📊 [UI PROGRESS] {percent}% - {msg}", flush=True)

input_file = "test_small_6pages.pdf"
output_file = "test_small_6pages_cleaned.pdf"

print(f"--- STARTING TEST PROCESSING ON 6-PAGE PDF ---")
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
    print(f"\n--- TEST FINISHED SUCCESSFULLY ---")
    print(f"File saved to: {output_file}")
    size = os.path.getsize(output_file)
    print(f"Output file size: {size / (1024*1024):.2f} MB")
else:
    print(f"\n--- TEST FAILED: {msg} ---")
