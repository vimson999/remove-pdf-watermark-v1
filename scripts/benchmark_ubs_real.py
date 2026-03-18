import time
import os
import fitz
from app.services.pdf_processor import PDFProcessor

def run_benchmark(file_path, engine="easyocr", do_ocr=True):
    processor = PDFProcessor(threshold=180) # UBS specific threshold
    output_name = f"benchmark_result_{engine}_{'ocr' if do_ocr else 'no_ocr'}.pdf"
    
    start_time = time.time()
    success, msg = processor.remove_watermark(
        file_path, output_name, do_ocr=do_ocr, ocr_engine=engine
    )
    duration = time.time() - start_time
    
    # Clean up output
    if os.path.exists(output_name):
        os.remove(output_name)
        
    return duration

if __name__ == "__main__":
    # Point to the new samples directory
    ubs_file = "../samples/瑞银-中国中免（601888）我们仍看好公司增长前景.pdf"
    if not os.path.exists(ubs_file):
        print(f"Error: {ubs_file} not found.")
        exit(1)
        
    doc = fitz.open(ubs_file)
    total_pages = len(doc)
    doc.close()
    
    print(f"🚀 Benchmarking UBS Report: {ubs_file} ({total_pages} pages)")
    print("-" * 60)
    
    # 1. Base Cleaning
    print("Testing Level 1: Bleaching Only...")
    t1 = run_benchmark(ubs_file, do_ocr=False)
    print(f"Result: {t1:.2f}s total | {t1/total_pages:.2f}s/page")
    
    # 2. EasyOCR (MPS)
    print("\nTesting Level 2: Bleaching + EasyOCR (MPS)...")
    t2 = run_benchmark(ubs_file, engine="easyocr", do_ocr=True)
    print(f"Result: {t2:.2f}s total | {t2/total_pages:.2f}s/page")
    
    # 3. PaddleOCR (CPU Optimized)
    print("\nTesting Level 3: Bleaching + PaddleOCR (CPU)...")
    t3 = run_benchmark(ubs_file, engine="paddleocr", do_ocr=True)
    print(f"Result: {t3:.2f}s total | {t3/total_pages:.2f}s/page")
    
    print("-" * 60)
    print(f"📊 Summary for 13-page UBS Cleaning:")
    print(f"  - No OCR      : {t1:.2f}s")
    print(f"  - EasyOCR     : {t2:.2f}s")
    print(f"  - PaddleOCR   : {t3:.2f}s")
