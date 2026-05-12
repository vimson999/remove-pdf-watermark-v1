from app.celery_utils import celery_app
from app.services.pdf_processor import PDFProcessor
import os
import logging
import time

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def process_pdf_task(self, input_path, output_path, mode, text_to_remove, threshold, do_redaction, do_header_clean, do_ocr=False, ocr_engine="easyocr"):
    """
    Background task to process a single PDF file.
    Updates state with progress information.
    """
    task_start = time.time()
    logger.info(f"🔔 [TASK START] ID: {self.request.id} | File: {os.path.basename(input_path)} | Engine: {ocr_engine}")
    
    try:
        def update_progress(msg, percent):
            self.update_state(state='PROGRESS', meta={'message': msg, 'percent': percent})
            # Noisy logs moved to debug if needed, but keeping primary milestones
            if percent % 20 == 0 or percent > 90:
                logger.info(f"📊 Task {self.request.id} Progress: {percent}% - {msg}")

        update_progress('初始化智能引擎...', 5)
        
        processor = PDFProcessor(threshold=threshold)
        
        # Pass the update_progress function as a callback
        success, message = processor.remove_watermark(
            input_path, 
            output_path, 
            mode=mode, 
            text_to_remove=text_to_remove,
            do_redaction=do_redaction,
            do_header_clean=do_header_clean,
            do_ocr=do_ocr,
            ocr_engine=ocr_engine,
            progress_callback=update_progress
        )
        
        duration = time.time() - task_start
        if success:
            logger.info(f"✨ [TASK SUCCESS] ID: {self.request.id} | Duration: {duration:.2f}s")
            return {
                'status': 'SUCCESS', 
                'message': '文件清洗完成', 
                'percent': 100, 
                'duration': round(duration, 1),
                'engine': ocr_engine if do_ocr else 'none'
            }
        else:
            logger.error(f"⚠️ [TASK FAILED] ID: {self.request.id} | Msg: {message}")
            return {'status': 'FAILURE', 'message': message, 'percent': 100, 'duration': duration}
            
    except Exception as e:
        duration = time.time() - task_start
        logger.error(f"💥 [TASK ERROR] ID: {self.request.id} | Error: {str(e)}", exc_info=True)
        return {'status': 'ERROR', 'message': str(e), 'percent': 100, 'duration': duration}
