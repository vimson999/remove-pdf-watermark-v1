from flask import Blueprint, render_template, request, send_file, redirect, url_for, flash, current_app, jsonify
import os
import logging
from app.utils import allowed_file, safe_filename
from app.tasks import process_pdf_task
from app.services.pdf_processor import PDFProcessor

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/analyze', methods=['POST'])
def analyze_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = safe_filename(file.filename)
        # Save to temp for analysis
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"temp_analyze_{filename}")
        try:
            file.save(temp_path)
            processor = PDFProcessor()
            analysis = processor.analyze_pdf(temp_path)
            # Remove temp file after analysis
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify(analysis)
        except Exception as e:
            logger.error(f"Analysis Route Error: {e}")
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

@main_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    files = request.files.getlist('files')
    mode = request.form.get('mode', 'image_bleach')
    text_to_remove = request.form.get('text_to_remove', '')
    threshold = int(request.form.get('threshold', 195))
    do_redaction = request.form.get('do_redaction') == 'on'
    do_header_clean = request.form.get('do_header_clean') == 'on'
    do_ocr = request.form.get('do_ocr') == 'on'
    ocr_engine = request.form.get('ocr_engine', 'easyocr')
    
    task_ids = []

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
            # Prepare output filename
            base_name = os.path.splitext(filename)[0]
            output_filename = f"{base_name}_cleaned.pdf"
            output_path = os.path.join(current_app.config['DOWNLOAD_FOLDER'], output_filename)
            
            # ASYNC: Submit Task
            task = process_pdf_task.delay(
                input_path, output_path, mode, text_to_remove, 
                threshold, do_redaction, do_header_clean, do_ocr, ocr_engine
            )
            task_ids.append({
                'filename': filename,
                'task_id': task.id,
                'output_filename': output_filename
            })
            
        except Exception as e:
            logger.error(f"UPLOAD ERROR: {e}")
            flash(f"Error saving/queueing {filename}")

    if not task_ids:
        return redirect(url_for('main.index'))

    return render_template('results.html', tasks=task_ids)

@main_bp.route('/status/<task_id>')
def task_status(task_id):
    task = process_pdf_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {'state': 'PENDING', 'percent': 0, 'status': 'Pending...'}
    elif task.state == 'PROGRESS':
        response = {'state': 'PROGRESS', 'percent': task.info.get('percent', 0), 'status': task.info.get('message', '')}
    elif task.state != 'FAILURE':
        # SUCCESS
        response = {'state': task.state, 'percent': 100, 'status': task.info.get('message', '')}
    else:
        # Something went wrong
        response = {'state': 'FAILURE', 'percent': 0, 'status': str(task.info)}
    return jsonify(response)

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
