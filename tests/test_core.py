import pytest
import os
import shutil
import fitz # type: ignore
from app import create_app
from app.services.pdf_processor import PDFProcessor

@pytest.fixture
def app():
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def clean_env(app):
    # Setup
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    yield
    # Teardown
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        shutil.rmtree(app.config['UPLOAD_FOLDER'])
    if os.path.exists(app.config['DOWNLOAD_FOLDER']):
        shutil.rmtree(app.config['DOWNLOAD_FOLDER'])

def test_processor_initialization():
    processor = PDFProcessor(threshold=200)
    assert processor.threshold == 200

def test_homepage(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"PDF" in response.data

def test_text_clean_processing(app, clean_env):
    """
    Test the Mode B (text_clean) logic:
    1. Create a dummy PDF with specific watermark text.
    2. Run the processor in text_clean mode.
    3. Verify the text is no longer searchable in the output PDF.
    """
    watermark_text = "SECRET_WATERMARK_123"
    input_pdf = os.path.join(app.config['UPLOAD_FOLDER'], "test_watermark.pdf")
    output_pdf = os.path.join(app.config['DOWNLOAD_FOLDER'], "test_cleaned.pdf")
    
    # 1. Generate a dummy PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "This is the main content.")
    page.insert_text((200, 200), watermark_text, fontsize=20, color=(0.8, 0.8, 0.8))
    doc.save(input_pdf)
    doc.close()
    
    # Verify watermark exists initially
    check_doc = fitz.open(input_pdf)
    assert check_doc[0].search_for(watermark_text)
    check_doc.close()
    
    # 2. Process the PDF
    processor = PDFProcessor()
    success, message = processor.remove_watermark(input_pdf, output_pdf, mode='text_clean', text_to_remove=watermark_text)
    
    # 3. Verify results
    assert success is True
    assert os.path.exists(output_pdf)
    
    # Check if watermark is gone
    final_doc = fitz.open(output_pdf)
    found_instances = final_doc[0].search_for(watermark_text)
    final_doc.close()
    
    assert len(found_instances) == 0, "Watermark text should have been removed."

def test_ocr_processing(app, clean_env):
    """
    Test Mode A (image_bleach) with OCR enabled.
    """
    input_pdf = os.path.join(app.config['UPLOAD_FOLDER'], "test_ocr.pdf")
    output_pdf = os.path.join(app.config['DOWNLOAD_FOLDER'], "test_ocr_cleaned.pdf")
    
    # 1. Generate a dummy PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Hello OCR World", fontsize=20, color=(0, 0, 0))
    doc.save(input_pdf)
    doc.close()
    
    # 2. Process the PDF
    processor = PDFProcessor()
    success, message = processor.remove_watermark(
        input_pdf, output_pdf, mode='image_bleach', 
        do_ocr=True, do_redaction=False, do_header_clean=False
    )
    
    # 3. Verify results
    assert success is True
    assert os.path.exists(output_pdf)
    
    # Verify the output PDF has text layer
    final_doc = fitz.open(output_pdf)
    page_text = final_doc[0].get_text()
    final_doc.close()
    
    assert len(page_text.strip()) > 0