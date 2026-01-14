import pytest
import os
import shutil
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
    shutil.rmtree(app.config['UPLOAD_FOLDER'])
    shutil.rmtree(app.config['DOWNLOAD_FOLDER'])

def test_processor_initialization():
    processor = PDFProcessor(threshold=200)
    assert processor.threshold == 200

def test_homepage(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"PDF" in response.data

def test_upload_no_file(client, clean_env):
    response = client.post('/upload', data={})
    assert response.status_code == 302 # Redirects

# Mocking file processing would be ideal here to avoid dependency on real PDFs,
# but for this integration test, we can check basic route logic.