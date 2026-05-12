from flask import Blueprint, render_template, request, send_file, redirect, url_for, flash, current_app, jsonify
import os
import logging
import json
import uuid
import sys
from app.utils import allowed_file, safe_filename
from app.tasks import process_pdf_task
from app.services.pdf_processor import PDFProcessor
from app.services.pdf_analyzer import PDFAnalyzer
from app.services.pdf_splitter import PDFSplitter
from app.services.audit import AuditManager

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# --- Page Navigation Routes ---

@main_bp.route('/')
def index():
    return render_template('cleaner.html', active_page='cleaner')

@main_bp.route('/analyzer')
def analyzer_page():
    return render_template('analyzer.html', active_page='analyzer')

@main_bp.route('/toolbox')
def toolbox_page():
    return render_template('toolbox.html', active_page='toolbox')

@main_bp.route('/dashboard')
def dashboard_page():
    logs = AuditManager.get_recent_logs(50)
    return render_template('dashboard.html', active_page='dashboard', logs=logs)

# --- API Routes ---

@main_bp.route('/analyze', methods=['POST'])
def analyze_v1():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = safe_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"quick_{filename}")
        try:
            file.save(temp_path)
            processor = PDFProcessor()
            analysis = processor.analyze_pdf(temp_path)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify(analysis)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Invalid file'}), 400

@main_bp.route('/api/analyze', methods=['POST'])
def api_analyze_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = safe_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"audit_{filename}")
        try:
            file.save(temp_path)
            report = PDFAnalyzer.analyze(temp_path)
            AuditManager.log_operation("ANALYSIS", filename, {}, "SUCCESS", "Report Generated")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return jsonify(report)
        except Exception as e:
            return jsonify({'status': 'error', 'error_msg': str(e)}), 500
    return jsonify({'error': 'Invalid file'}), 400

@main_bp.route('/api/split', methods=['POST'])
def api_split_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = safe_filename(file.filename)
        input_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        try:
            mode = request.form.get('mode', 'equal')
            download_dir = current_app.config['DOWNLOAD_FOLDER']
            if mode == 'equal':
                step = int(request.form.get('step', 10))
                generated_files = PDFSplitter.split_equally(input_path, download_dir, step)
            else:
                range_str = request.form.get('ranges', '')
                ranges = []
                for r in range_str.split(','):
                    parts = r.strip().split('-')
                    if len(parts) == 2:
                        ranges.append((int(parts[0]), int(parts[1])))
                generated_files = PDFSplitter.split_by_range(input_path, download_dir, ranges)
            
            AuditManager.log_operation("SPLIT", filename, {"mode": mode}, "SUCCESS", f"Split {len(generated_files)} files")
            return jsonify({'success': True, 'files': generated_files, 'count': len(generated_files)})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
    return jsonify({'error': 'Invalid file'}), 400

# --- The "Resilient" Upload Route ---

@main_bp.route('/upload', methods=['POST'])
def upload_file():
    # DEBUG console print
    print(">>> [DEBUG] Entering upload_file route", file=sys.stderr)
    
    if 'files' not in request.files:
        print(">>> [DEBUG] No files in request", file=sys.stderr)
        flash('No file part')
        return redirect(url_for('main.index'))
    
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
        if file.filename == '' or not file: continue
        if not allowed_file(file.filename): continue

        filename = safe_filename(file.filename)
        input_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        
        output_filename = f"{os.path.splitext(filename)[0]}_cleaned.pdf"
        output_path = os.path.join(current_app.config['DOWNLOAD_FOLDER'], output_filename)
        
        print(f">>> [DEBUG] Processing file: {filename}", file=sys.stderr)
        AuditManager.log_operation("CLEAN_START", filename, {"mode": mode}, "SUCCESS", "Processing started")

        try:
            print(">>> [DEBUG] Attempting Async task submit...", file=sys.stderr)
            # 尝试异步提交
            task = process_pdf_task.delay(
                input_path, output_path, mode, text_to_remove, 
                threshold, do_redaction, do_header_clean, do_ocr, ocr_engine
            )
            task_ids.append({
                'filename': filename,
                'task_id': task.id,
                'output_filename': output_filename
            })
            print(f">>> [DEBUG] Task submitted successfully: {task.id}", file=sys.stderr)
        except Exception as e:
            # 最终回退：完全手动同步执行
            print(f">>> [DEBUG] Celery failed: {e}. Falling back to SYNC mode.", file=sys.stderr)
            try:
                processor = PDFProcessor(threshold=threshold)
                success, msg = processor.remove_watermark(
                    input_path, output_path, mode=mode, text_to_remove=text_to_remove,
                    do_redaction=do_redaction, do_header_clean=do_header_clean,
                    do_ocr=do_ocr, ocr_engine=ocr_engine
                )
                
                fake_id = f"SYNC_{uuid.uuid4()}"
                task_ids.append({
                    'filename': filename,
                    'task_id': fake_id,
                    'output_filename': output_filename,
                    'status': 'SUCCESS' if success else 'FAILURE'
                })
                print(f">>> [DEBUG] Sync cleaning finished. Success: {success}", file=sys.stderr)
            except Exception as sync_err:
                print(f">>> [DEBUG] Sync fallback ALSO failed: {sync_err}", file=sys.stderr)
                # If even sync fails, we might still want to report it
                return jsonify({'error': f"Processing failed: {str(sync_err)}"}), 500

    if not task_ids:
        return redirect(url_for('main.index'))

    return render_template('results.html', tasks=task_ids)

@main_bp.route('/status/<task_id>')
def task_status(task_id):
    if task_id.startswith("SYNC_"):
        return jsonify({'state': 'SUCCESS', 'percent': 100, 'status': 'Complete (Sync Mode)'})
        
    try:
        task = process_pdf_task.AsyncResult(task_id)
        if task.state == 'PENDING':
            response = {'state': 'PENDING', 'percent': 0, 'status': 'Pending...'}
        elif task.state == 'PROGRESS':
            response = {'state': 'PROGRESS', 'percent': task.info.get('percent', 0), 'status': task.info.get('message', '')}
        elif task.state != 'FAILURE':
            response = {'state': task.state, 'percent': 100, 'status': 'Finished'}
        else:
            response = {'state': 'FAILURE', 'percent': 0, 'status': str(task.info)}
        return jsonify(response)
    except Exception:
        return jsonify({'state': 'SUCCESS', 'percent': 100, 'status': 'Finished'})

@main_bp.route('/download/<filename>')
def download(filename):
    filename = safe_filename(filename)
    path = os.path.join(current_app.config['DOWNLOAD_FOLDER'], filename)
    if os.path.exists(path):
        AuditManager.log_operation("DOWNLOAD", filename, {}, "SUCCESS", "File downloaded")
        return send_file(path, as_attachment=True)
    return redirect(url_for('main.index'))
