from app.services.pdf_processor import PDFProcessor
import os

processor = PDFProcessor()

files = [
    "瑞银-中国中免（601888）我们仍看好公司增长前景.pdf",
    "野村证券-亚洲洞察：霍尔木兹海峡在中国能源供应中的角色-260303_副本.pdf",
    "test_small_6pages.pdf"
]

for f in files:
    if os.path.exists(f):
        print(f"\nAnalyzing: {f}")
        res = processor.analyze_pdf(f)
        print(f"Type: {res['type']}")
        print(f"Threshold: {res['threshold']}")
        print(f"OCR: {res['do_ocr']}")
        print(f"Details: {res['details']}")
