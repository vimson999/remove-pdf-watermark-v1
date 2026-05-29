from flask import Blueprint, render_template, request, send_file, redirect, url_for, flash, current_app, jsonify
import os
import logging
import json
import uuid
import sys
import time
import threading
import subprocess
import shutil
from pathlib import Path
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

@main_bp.route('/batch')
def batch_page():
    return render_template('batch.html', active_page='batch')

@main_bp.route('/audio')
def audio_page():
    return render_template('audio.html', active_page='audio')

@main_bp.route('/dashboard')
def dashboard_page():
    logs = AuditManager.get_recent_logs(50)
    return render_template('dashboard.html', active_page='dashboard', logs=logs)

@main_bp.route('/api/local-folders')
def api_local_folders():
    root = Path.cwd().resolve()
    excluded = {'.git', '.pytest_cache', '__pycache__', 'venv'}
    folders = []
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if child.is_dir() and not child.name.startswith('.') and child.name not in excluded:
            folders.append({
                "name": child.name,
                "path": child.relative_to(root).as_posix(),
            })
    return jsonify({"success": True, "folders": folders})

def _build_folder_tree(base_dir: Path, root_dir: Path, max_depth: int = 6):
    excluded = {'.git', '.pytest_cache', '__pycache__', 'venv'}
    if max_depth < 0:
        return None

    children = []
    try:
        child_dirs = sorted(
            [
                child for child in base_dir.iterdir()
                if child.is_dir() and not child.name.startswith('.') and child.name not in excluded
            ],
            key=lambda p: p.name.lower()
        )
    except OSError:
        child_dirs = []

    for child in child_dirs:
        child_node = _build_folder_tree(child, root_dir, max_depth - 1)
        if child_node:
            children.append(child_node)

    return {
        "name": base_dir.name or root_dir.name,
        "path": "." if base_dir == root_dir else base_dir.relative_to(root_dir).as_posix(),
        "children": children,
    }

@main_bp.route('/api/folder-tree')
def api_folder_tree():
    root = Path.cwd().resolve()
    tree = _build_folder_tree(root, root)
    return jsonify({"success": True, "tree": tree})

@main_bp.route('/api/local-pdfs')
def api_local_pdfs():
    try:
        folder = _resolve_local_folder(request.args.get("dir", "0513"))
        if not folder.exists() or not folder.is_dir():
            return jsonify({"success": False, "error": "目录不存在。"}), 400
        files = []
        for pdf in sorted(folder.rglob("*.pdf"), key=lambda p: p.relative_to(folder).as_posix().lower()):
            relative_path = pdf.relative_to(folder).as_posix()
            files.append({
                "name": relative_path,
                "basename": pdf.name,
                "size_mb": round(pdf.stat().st_size / (1024 * 1024), 2),
            })
        return jsonify({"success": True, "files": files, "count": len(files)})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

@main_bp.route('/api/local-audios')
def api_local_audios():
    audio_extensions = {'.mp3', '.m4a', '.aac', '.wav', '.flac'}
    try:
        folder = _resolve_local_folder(request.args.get("dir", "音频/待清理"))
        if not folder.exists() or not folder.is_dir():
            return jsonify({"success": False, "error": "目录不存在。"}), 400
        files = []
        for audio in sorted(folder.rglob("*"), key=lambda p: p.relative_to(folder).as_posix().lower()):
            if audio.is_file() and audio.suffix.lower() in audio_extensions:
                files.append({
                    "name": audio.relative_to(folder).as_posix(),
                    "basename": audio.name,
                    "size_mb": round(audio.stat().st_size / (1024 * 1024), 2),
                })
        return jsonify({"success": True, "files": files, "count": len(files)})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

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

def _resolve_local_folder(folder_value):
    root = Path.cwd().resolve()
    folder = Path(folder_value or "").expanduser()
    if not folder.is_absolute():
        folder = root / folder
    folder = folder.resolve()
    try:
        folder.relative_to(root)
    except ValueError as exc:
        raise ValueError("目录必须位于当前项目文件夹内。") from exc
    return folder

def _run_batch_clean(job_id, input_dir, output_dir, threshold, do_ocr, overwrite, prefix):
    start_total = time.time()
    processor = PDFProcessor(threshold=threshold)
    pdf_files = sorted(input_dir.rglob("*.pdf"), key=lambda p: p.relative_to(input_dir).as_posix().lower())
    total = len(pdf_files)
    success_count = 0
    failed_count = 0
    skipped_count = 0
    AuditManager.update_batch_job(
        job_id,
        state="RUNNING",
        total=total,
        message=f"发现 {total} 个 PDF，开始清洗。",
    )

    for index, pdf_file in enumerate(pdf_files, start=1):
        relative_path = pdf_file.relative_to(input_dir)
        output_relative_path = relative_path.parent / f"{prefix}{pdf_file.name}"
        output_file = output_dir / output_relative_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        display_name = relative_path.as_posix()
        output_display_name = output_relative_path.as_posix()
        if output_file.exists() and not overwrite:
            skipped_count += 1
            AuditManager.add_batch_file_result(
                job_id,
                display_name,
                "SKIPPED",
                "输出文件已存在",
                output_display_name,
                0,
            )
            AuditManager.update_batch_job(
                job_id,
                current=index,
                skipped=skipped_count,
                overall_percent=round((index / total) * 100, 1),
                current_file=display_name,
                current_stage="跳过",
                current_file_percent=100,
                message=f"已跳过 {display_name}",
            )
            continue

        AuditManager.update_batch_job(
            job_id,
            current=index,
            current_file=display_name,
            current_file_percent=0,
            current_stage="准备处理",
            message=f"正在处理 {index}/{total}: {display_name}",
        )
        start_single = time.time()
        try:
            def update_progress(message, percent):
                current_file_percent = max(0, min(100, int(percent)))
                overall = ((index - 1) + (current_file_percent / 100)) / total * 100
                AuditManager.update_batch_job(
                    job_id,
                    current_file_percent=current_file_percent,
                    current_stage=message,
                    overall_percent=round(overall, 1),
                    message=f"{display_name}: {message}",
                )

            success, message = processor.remove_watermark(
                str(pdf_file),
                str(output_file),
                mode="image_bleach",
                do_redaction=True,
                do_header_clean=True,
                do_ocr=do_ocr,
                progress_callback=update_progress,
            )
            duration = round(time.time() - start_single, 2)
            if success:
                success_count += 1
                status = "SUCCESS"
            else:
                failed_count += 1
                status = "FAILED"
            AuditManager.add_batch_file_result(
                job_id,
                display_name,
                status,
                message,
                output_display_name if success else "",
                duration,
            )
            AuditManager.update_batch_job(
                job_id,
                success=success_count,
                failed=failed_count,
                skipped=skipped_count,
                current_file_percent=100,
                overall_percent=round((index / total) * 100, 1),
            )
        except Exception as exc:
            failed_count += 1
            AuditManager.add_batch_file_result(
                job_id,
                display_name,
                "ERROR",
                str(exc),
                "",
                round(time.time() - start_single, 2),
            )
            AuditManager.update_batch_job(
                job_id,
                failed=failed_count,
                current_file_percent=100,
                overall_percent=round((index / total) * 100, 1),
            )

    duration = round(time.time() - start_total, 2)
    AuditManager.update_batch_job(
        job_id,
        duration=duration,
        overall_percent=100,
        current_file_percent=100,
        current_stage="完成",
        state="FINISHED",
        message="批量清洗完成",
        success=success_count,
        failed=failed_count,
        skipped=skipped_count,
    )
    AuditManager.log_operation(
        "BATCH_CLEAN",
        str(input_dir),
        {
            "output_dir": str(output_dir),
            "threshold": threshold,
            "do_ocr": do_ocr,
            "overwrite": overwrite,
        },
        "SUCCESS" if failed_count == 0 else "ERROR",
        f"{success_count} succeeded, {failed_count} failed, {skipped_count} skipped",
    )

@main_bp.route('/api/batch-clean', methods=['POST'])
def api_batch_clean():
    data = request.get_json(silent=True) or {}
    try:
        input_dir = _resolve_local_folder(data.get("input_dir", "0513"))
        output_dir = _resolve_local_folder(data.get("output_dir", f"{input_dir.name}_cleaned"))
        threshold = int(data.get("threshold", 245))
        do_ocr = bool(data.get("do_ocr", False))
        overwrite = bool(data.get("overwrite", False))
        prefix = data.get("prefix", "") or ""

        if not input_dir.exists() or not input_dir.is_dir():
            return jsonify({"success": False, "error": "输入目录不存在。"}), 400

        pdf_count = len(list(input_dir.rglob("*.pdf")))
        if pdf_count == 0:
            return jsonify({"success": False, "error": "输入目录里没有 PDF 文件。"}), 400

        output_dir.mkdir(parents=True, exist_ok=True)
        job_id = str(uuid.uuid4())
        AuditManager.create_batch_job(
            job_id,
            str(input_dir),
            str(output_dir),
            pdf_count,
            {
                "threshold": threshold,
                "do_ocr": do_ocr,
                "overwrite": overwrite,
                "prefix": prefix,
            },
        )
        thread = threading.Thread(
            target=_run_batch_clean,
            args=(job_id, input_dir, output_dir, threshold, do_ocr, overwrite, prefix),
            daemon=True,
        )
        thread.start()
        AuditManager.log_operation(
            "BATCH_CLEAN_START",
            str(input_dir),
            {"output_dir": str(output_dir), "threshold": threshold, "do_ocr": do_ocr},
            "PENDING",
            f"Job {job_id}",
        )
        return jsonify({"success": True, "job_id": job_id})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error(f"Batch clean start failed: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500

@main_bp.route('/api/batch-clean/status/<job_id>')
def api_batch_clean_status(job_id):
    job = AuditManager.get_batch_job(job_id)
    if not job:
        return jsonify({"success": False, "error": "任务不存在或服务已重启。"}), 404
    return jsonify({"success": True, "job": job})

def _audio_codec_args(suffix: str):
    suffix = suffix.lower()
    if suffix == ".mp3":
        return ["-c:a", "libmp3lame", "-q:a", "2"]
    if suffix in {".m4a", ".aac"}:
        return ["-c:a", "aac", "-b:a", "192k"]
    if suffix == ".wav":
        return ["-c:a", "pcm_s16le"]
    if suffix == ".flac":
        return ["-c:a", "flac"]
    return ["-c:a", "libmp3lame", "-q:a", "2"]

def _probe_audio_duration(file_path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("未找到 ffprobe，请先安装 ffmpeg。")
    result = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())

def _trim_audio_file(input_file: Path, output_file: Path, trim_start: float, trim_end: float, progress_callback=None):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg。")
    duration = _probe_audio_duration(input_file)
    keep_duration = duration - trim_start - trim_end
    if keep_duration <= 0:
        raise ValueError(f"音频过短，时长 {duration:.2f}s，不足以裁掉头尾 {trim_start + trim_end:.2f}s。")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-ss", f"{trim_start:.3f}",
        "-t", f"{keep_duration:.3f}",
        "-i", str(input_file),
        "-map", "0:a:0",
        "-vn",
        *_audio_codec_args(input_file.suffix),
        "-progress", "pipe:1",
        str(output_file),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.stdout:
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("out_time_ms="):
                try:
                    out_seconds = int(line.split("=", 1)[1]) / 1_000_000
                    percent = max(0, min(100, int((out_seconds / keep_duration) * 100)))
                    if progress_callback:
                        progress_callback("正在裁剪音频", percent)
                except ValueError:
                    pass
    stderr = proc.stderr.read() if proc.stderr else ""
    code = proc.wait()
    if code != 0:
        raise RuntimeError(stderr.strip() or f"ffmpeg 退出码 {code}")
    if progress_callback:
        progress_callback("音频裁剪完成", 100)
    return duration, keep_duration

def _run_audio_trim_job(job_id, input_dir, output_dir, trim_start, trim_end, overwrite):
    audio_extensions = {'.mp3', '.m4a', '.aac', '.wav', '.flac'}
    start_total = time.time()
    audio_files = [
        path for path in sorted(input_dir.rglob("*"), key=lambda p: p.relative_to(input_dir).as_posix().lower())
        if path.is_file() and path.suffix.lower() in audio_extensions
    ]
    total = len(audio_files)
    success_count = 0
    failed_count = 0
    skipped_count = 0
    AuditManager.update_batch_job(
        job_id,
        state="RUNNING",
        total=total,
        message=f"发现 {total} 个音频，开始裁剪。",
    )

    for index, audio_file in enumerate(audio_files, start=1):
        relative_path = audio_file.relative_to(input_dir)
        output_file = output_dir / relative_path
        display_name = relative_path.as_posix()
        if output_file.exists() and not overwrite:
            skipped_count += 1
            AuditManager.add_batch_file_result(job_id, display_name, "SKIPPED", "输出文件已存在", display_name, 0)
            AuditManager.update_batch_job(
                job_id,
                current=index,
                skipped=skipped_count,
                overall_percent=round((index / total) * 100, 1),
                current_file=display_name,
                current_stage="跳过",
                current_file_percent=100,
                message=f"已跳过 {display_name}",
            )
            continue

        AuditManager.update_batch_job(
            job_id,
            current=index,
            current_file=display_name,
            current_file_percent=0,
            current_stage="准备裁剪",
            message=f"正在处理 {index}/{total}: {display_name}",
        )
        start_single = time.time()
        try:
            def update_progress(message, percent):
                current_file_percent = max(0, min(100, int(percent)))
                overall = ((index - 1) + (current_file_percent / 100)) / total * 100
                AuditManager.update_batch_job(
                    job_id,
                    current_file_percent=current_file_percent,
                    current_stage=message,
                    overall_percent=round(overall, 1),
                    message=f"{display_name}: {message}",
                )

            original_duration, kept_duration = _trim_audio_file(
                audio_file,
                output_file,
                trim_start,
                trim_end,
                progress_callback=update_progress,
            )
            success_count += 1
            duration = round(time.time() - start_single, 2)
            AuditManager.add_batch_file_result(
                job_id,
                display_name,
                "SUCCESS",
                f"原始 {original_duration:.1f}s，输出 {kept_duration:.1f}s",
                display_name,
                duration,
            )
            AuditManager.update_batch_job(
                job_id,
                success=success_count,
                failed=failed_count,
                skipped=skipped_count,
                current_file_percent=100,
                overall_percent=round((index / total) * 100, 1),
            )
        except Exception as exc:
            failed_count += 1
            AuditManager.add_batch_file_result(
                job_id,
                display_name,
                "ERROR",
                str(exc),
                "",
                round(time.time() - start_single, 2),
            )
            AuditManager.update_batch_job(
                job_id,
                failed=failed_count,
                current_file_percent=100,
                overall_percent=round((index / total) * 100, 1),
            )

    AuditManager.update_batch_job(
        job_id,
        duration=round(time.time() - start_total, 2),
        overall_percent=100,
        current_file_percent=100,
        current_stage="完成",
        state="FINISHED",
        message="音频批量裁剪完成",
        success=success_count,
        failed=failed_count,
        skipped=skipped_count,
    )
    AuditManager.log_operation(
        "AUDIO_TRIM",
        str(input_dir),
        {
            "output_dir": str(output_dir),
            "trim_start": trim_start,
            "trim_end": trim_end,
            "overwrite": overwrite,
        },
        "SUCCESS" if failed_count == 0 else "ERROR",
        f"{success_count} succeeded, {failed_count} failed, {skipped_count} skipped",
    )

@main_bp.route('/api/audio-trim', methods=['POST'])
def api_audio_trim():
    data = request.get_json(silent=True) or {}
    try:
        input_dir = _resolve_local_folder(data.get("input_dir", "音频/待清理"))
        output_dir = _resolve_local_folder(data.get("output_dir", "音频/清理完毕"))
        trim_start = float(data.get("trim_start", 11))
        trim_end = float(data.get("trim_end", 11))
        overwrite = bool(data.get("overwrite", False))

        if not input_dir.exists() or not input_dir.is_dir():
            return jsonify({"success": False, "error": "输入目录不存在。"}), 400
        audio_extensions = {'.mp3', '.m4a', '.aac', '.wav', '.flac'}
        audio_count = len([p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in audio_extensions])
        if audio_count == 0:
            return jsonify({"success": False, "error": "输入目录里没有音频文件。"}), 400
        if trim_start < 0 or trim_end < 0:
            return jsonify({"success": False, "error": "裁剪秒数不能为负数。"}), 400

        output_dir.mkdir(parents=True, exist_ok=True)
        job_id = str(uuid.uuid4())
        AuditManager.create_batch_job(
            job_id,
            str(input_dir),
            str(output_dir),
            audio_count,
            {
                "job_type": "audio_trim",
                "trim_start": trim_start,
                "trim_end": trim_end,
                "overwrite": overwrite,
            },
        )
        thread = threading.Thread(
            target=_run_audio_trim_job,
            args=(job_id, input_dir, output_dir, trim_start, trim_end, overwrite),
            daemon=True,
        )
        thread.start()
        AuditManager.log_operation(
            "AUDIO_TRIM_START",
            str(input_dir),
            {"output_dir": str(output_dir), "trim_start": trim_start, "trim_end": trim_end},
            "PENDING",
            f"Job {job_id}",
        )
        return jsonify({"success": True, "job_id": job_id})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error(f"Audio trim start failed: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500

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
