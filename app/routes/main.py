from flask import Blueprint, render_template, request, send_file, redirect, url_for, flash, current_app
import os
import logging
from app.services.pdf_processor import PDFProcessor
from app.utils import allowed_file, safe_filename

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    files = request.files.getlist('files')
    processed_files = []
    
    # In future versions, threshold could be a request parameter
    processor = PDFProcessor(threshold=200)

    for file in files:
        if file.filename == '' or not file:
            continue
        
        if not allowed_file(file.filename):
            flash(f"Skipped {file.filename}: Invalid extension.")
            continue

        filename = safe_filename(file.filename)
        input_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(input_path)
        except Exception as e:
            logger.error(f"Failed to save file {filename}: {e}")
            flash(f"Error saving {filename}")
            continue
        
        # Prepare output filename
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_cleaned.pdf"
        output_path = os.path.join(current_app.config['DOWNLOAD_FOLDER'], output_filename)
        
        # Call Service
        success, message = processor.remove_watermark(input_path, output_path)
        
        if success:
            processed_files.append(output_filename)
        else:
            flash(f"Error processing {filename}: {message}")
            logger.error(f"Failed to process {filename}: {message}")

    if not processed_files:
        return redirect(url_for('main.index'))

    return render_template('results.html', files=processed_files)

@main_bp.route('/download/<filename>')
def download(filename):
    # Security Check: Prevent Path Traversal
    filename = safe_filename(filename)
    path = os.path.join(current_app.config['DOWNLOAD_FOLDER'], filename)
    
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    else:
        flash("File not found.")
        return redirect(url_for('main.index'))
