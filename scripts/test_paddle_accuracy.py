import fitz
import cv2
import numpy as np
import time
import os
from paddleocr import PaddleOCR
import easyocr
import torch

def test_ocr_comparison(pdf_path, page_idx=0):
    print(f"--- OCR Comparison on {pdf_path} (Page {page_idx}) ---")
    
    # 1. Render Page
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=200)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    # 2. EasyOCR (Current)
    print("\n[EasyOCR] Initializing...")
    use_mps = torch.backends.mps.is_available()
    reader_easy = easyocr.Reader(['ch_sim', 'en'], gpu=use_mps)
    
    start = time.time()
    results_easy = reader_easy.readtext(img)
    duration_easy = time.time() - start
    print(f"EasyOCR Time: {duration_easy:.2f}s (MPS: {use_mps})")
    print(f"EasyOCR Detections: {len(results_easy)}")
    
    # 3. PaddleOCR (New)
    print("\n[PaddleOCR] Initializing...")
    # lang='ch' includes both Chinese and English
    # Let's try to initialize with minimal params to use default mobile models
    # We specify ocr_version="PP-OCRv4" which typically defaults to mobile lightweight models
    reader_paddle = PaddleOCR(lang="ch", ocr_version="PP-OCRv4")
    
    start = time.time()
    # Direct predict is recommended in 3.4.0
    results_paddle = reader_paddle.predict(img)
    duration_paddle = time.time() - start
    
    print(f"PaddleOCR Time: {duration_paddle:.2f}s")
    if results_paddle and len(results_paddle) > 0:
        res_dict = results_paddle[0]
        if isinstance(res_dict, dict) and 'rec_texts' in res_dict:
            texts = res_dict.get('rec_texts', [])
            scores = res_dict.get('rec_scores', [])
            polys = res_dict.get('rec_polys', [])
            count_paddle = len(texts)
            print(f"PaddleOCR Detections: {count_paddle}")

            print("\n--- Sample Comparison (Top 5) ---")
            print(f"{'Engine':<12} | {'Text':<30} | {'Conf':<6}")
            print("-" * 55)
            
            for i, res in enumerate(results_easy[:5]):
                text = res[1][:28] + ".." if len(res[1]) > 28 else res[1]
                print(f"{'EasyOCR':<12} | {text:<30} | {res[2]:.4f}")
                
            for i in range(min(5, count_paddle)):
                text_str = texts[i]
                score = scores[i]
                text = text_str[:28] + ".." if len(text_str) > 28 else text_str
                print(f"{'PaddleOCR':<12} | {text:<30} | {score:.4f}")
        else:
            print("PaddleOCR returned unknown format.")
            print(res_dict)

    doc.close()

if __name__ == "__main__":
    test_pdf = "test_small_6pages.pdf"
    if os.path.exists(test_pdf):
        test_ocr_comparison(test_pdf)
    else:
        print(f"Error: {test_pdf} not found.")
