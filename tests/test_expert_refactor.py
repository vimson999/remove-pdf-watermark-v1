import os
import sys
import fitz
import numpy as np
import pytest
from app.services.pdf_processor import PDFProcessor, _get_ocr_provider, _bleach_image

# Mocking env for standalone test
def test_strategy_initialization():
    print("\n[TEST] Testing OCR Provider Strategy...")
    # Test EasyOCR
    provider_easy = _get_ocr_provider("easyocr")
    assert provider_easy is not None
    assert provider_easy.engine_name == "easyocr"
    
    # Test PaddleOCR
    provider_paddle = _get_ocr_provider("paddleocr")
    assert provider_paddle is not None
    assert provider_paddle.engine_name == "paddleocr"

def test_bleach_logic_atomicity():
    print("\n[TEST] Testing Bleach Logic Atomicity...")
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8) + 200 # Light gray
    bleached, duration = _bleach_image(dummy_img.copy(), 195, False)
    # With threshold 195, 200 should turn white (255)
    assert bleached[0, 0, 0] == 255
    assert duration > 0

def test_coordinate_mapping():
    print("\n[TEST] Testing Coordinate Mapping Accuracy...")
    # Paddle results usually look like: [[x,y], [x,y], [x,y], [x,y]]
    fake_poly = [[10.5, 20.0], [100.2, 20.0], [100.2, 50.8], [10.5, 50.8]]
    # We manually simulate what PaddleOCRProvider.read_text does
    xs = [p[0] for p in fake_poly]
    ys = [p[1] for p in fake_poly]
    rect = [min(xs), min(ys), max(xs), max(ys)]
    
    # PyMuPDF Rect check
    fitz_rect = fitz.Rect(rect[0], rect[1], rect[2], rect[3])
    assert fitz_rect.width > 80
    assert fitz_rect.height > 30

def test_full_pipeline_with_test_pdf():
    print("\n[TEST] Testing Full Refactored Pipeline...")
    processor = PDFProcessor()
    test_pdf = "test_small_6pages.pdf"
    output_pdf = "test_refactored_output.pdf"
    
    if os.path.exists(test_pdf):
        success, msg = processor.remove_watermark(
            test_pdf, output_pdf, do_ocr=True, ocr_engine="easyocr"
        )
        assert success is True
        assert os.path.exists(output_pdf)
        os.remove(output_pdf)
    else:
        pytest.skip("Test PDF not found.")

if __name__ == "__main__":
    # Manual run if not via pytest
    try:
        test_strategy_initialization()
        test_bleach_logic_atomicity()
        test_coordinate_mapping()
        test_full_pipeline_with_test_pdf()
        print("\n✅ All Expert Benchmark Tests Passed!")
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
