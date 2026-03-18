import sys
import logging
from app.services.pdf_processor import PDFProcessor

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

def progress(msg, percent):
    print(f"[{percent}%] {msg}", flush=True)

input_file = "瑞银-中国中免（601888）我们仍看好公司增长前景.pdf"
output_file = "瑞银-中国中免（601888）我们仍看好公司增长前景_V2_cleaned.pdf"

print(f"Starting to process {input_file} with refined logic...")
processor = PDFProcessor(threshold=180) # Use more aggressive threshold
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
    print(f"\nSuccess! File saved to {output_file}")
else:
    print(f"\nError: {msg}")
