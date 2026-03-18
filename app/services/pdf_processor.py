import fitz  # type: ignore
import cv2
import numpy as np
from PIL import Image
import logging
import os
import time
from pathlib import Path
from typing import Tuple, Optional, List, Dict
from concurrent.futures import ProcessPoolExecutor, as_completed

# Configure module-level logger
logger = logging.getLogger(__name__)

# Global variable for OCR model inside worker processes to avoid reloading
_global_ocr_reader = None
_global_ocr_engine_name = "easyocr"

def _init_worker_ocr(languages: List[str], engine: str = "easyocr"):
    """
    Initialize the OCR reader once per worker process.
    """
    global _global_ocr_reader, _global_ocr_engine_name
    _global_ocr_engine_name = engine
    try:
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        
        if engine == "paddleocr":
            from paddleocr import PaddleOCR
            # Use Mobile models for speed since CPU inference of server models takes >100s per page.
            # PP-OCRv4 defaults to mobile and takes ~4s on M1 CPU.
            _global_ocr_reader = PaddleOCR(lang="ch", ocr_version="PP-OCRv4")
            print(f"OCR Worker Init Success (Engine: PaddleOCR)")
        else:
            import easyocr
            import torch
            # Use MPS (Metal Performance Shaders) if available on Apple Silicon
            use_gpu = torch.backends.mps.is_available()
            _global_ocr_reader = easyocr.Reader(languages, gpu=use_gpu)
            print(f"OCR Worker Init Success (Engine: EasyOCR, GPU/MPS: {use_gpu})")
    except Exception as e:
        print(f"OCR Worker Init Error: {e}")

def _process_page_parallel(page_index: int, img_bytes: bytes, threshold: int, 
                          do_header_clean: bool, do_ocr: bool, ocr_engine: str = "easyocr") -> Dict:
    """
    Worker function to process a single page: bleach + OCR.
    """
    start_time = time.time()
    
    # 1. Decode image
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return {'index': page_index, 'success': False, 'error': 'Image decode failed'}

    # 2. Bleaching
    bleach_start = time.time()
    _, thresh_img = cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), threshold, 255, cv2.THRESH_BINARY)
    img[thresh_img == 255] = [255, 255, 255]
    
    if do_header_clean:
        h, w = img.shape[:2]
        header_h = int(h * 0.08)
        header_area = img[0:header_h, :]
        header_gray = cv2.cvtColor(header_area, cv2.COLOR_BGR2GRAY)
        header_mask = cv2.threshold(header_gray, 150, 255, cv2.THRESH_BINARY)[1]
        header_area[header_mask == 255] = [255, 255, 255]
        blue_mask = (header_area[:,:,0] > 150) & (header_area[:,:,1] < 150) & (header_area[:,:,2] < 150)
        header_area[blue_mask] = [255, 255, 255]
    bleach_duration = time.time() - bleach_start

    # 3. OCR
    ocr_results = []
    ocr_duration = 0
    if do_ocr:
        ocr_start = time.time()
        global _global_ocr_reader, _global_ocr_engine_name
        
        # Reload reader if engine changed or not initialized
        if _global_ocr_reader is None or _global_ocr_engine_name != ocr_engine:
            _init_worker_ocr(['ch_sim', 'en'], engine=ocr_engine)
            
        if _global_ocr_reader:
            try:
                if ocr_engine == "paddleocr":
                    # PaddleOCR 3.4.0+ predict() returns a list of dicts
                    raw_results = _global_ocr_reader.predict(img)
                    if raw_results and len(raw_results) > 0:
                        res_dict = raw_results[0]
                        if isinstance(res_dict, dict) and 'rec_texts' in res_dict:
                            texts = res_dict.get('rec_texts', [])
                            scores = res_dict.get('rec_scores', [])
                            polys = res_dict.get('rec_polys', [])
                            
                            for i in range(len(texts)):
                                text = texts[i]
                                prob = float(scores[i])
                                bbox = polys[i]
                                
                                if prob < 0.3 or not text.strip(): continue
                                
                                # Filtering
                                norm = text.lower().replace(" ", "")
                                if any(p in norm for p in ["知识星球", "vxfccnn88", "evaluationonly", "ripper"]):
                                    continue
                                
                                # Extract min/max bounds from polygon
                                xs = [p[0] for p in bbox]
                                ys = [p[1] for p in bbox]
                                ocr_results.append({
                                    'bbox': [[float(min(xs)), float(min(ys))], [float(max(xs)), float(min(ys))], [float(max(xs)), float(max(ys))], [float(min(xs)), float(max(ys))]],
                                    'text': text, 
                                    'prob': prob
                                })
                else:
                    # EasyOCR
                    raw_results = _global_ocr_reader.readtext(img)
                    for (bbox, text, prob) in raw_results:
                        if prob < 0.3 or not text.strip(): continue
                        
                        norm = text.lower().replace(" ", "")
                        if any(p in norm for p in ["知识星球", "vxfccnn88", "evaluationonly", "ripper"]):
                            continue
                            
                        ocr_results.append({'bbox': bbox, 'text': text, 'prob': prob})
            except Exception as e:
                print(f"OCR Execution Error on page {page_index} ({ocr_engine}): {e}")
        ocr_duration = time.time() - ocr_start

    # 4. Re-encode bleached image
    encode_success, buffer = cv2.imencode('.png', img)
    if not encode_success:
        return {'index': page_index, 'success': False, 'error': 'Image encode failed'}

    return {
        'index': page_index,
        'success': True,
        'img_data': buffer.tobytes(),
        'ocr_results': ocr_results,
        'metrics': {
            'bleach': bleach_duration,
            'ocr': ocr_duration,
            'total': time.time() - start_time
        },
        'dimensions': (img.shape[1], img.shape[0]) # (w, h)
    }

class PDFProcessor:
    def __init__(self, threshold: int = 195):
        self.threshold = threshold

    def remove_watermark(self, input_path: str, output_path: str, mode: str = 'image_bleach', 
                         text_to_remove: str = "", do_redaction: bool = True, 
                         do_header_clean: bool = True, do_ocr: bool = False, 
                         ocr_engine: str = "easyocr", progress_callback=None) -> Tuple[bool, str]:
        doc = None
        start_time = time.time()
        try:
            logger.info(f"🚀 [START] Processing: {input_path} (Mode: {mode}, OCR: {do_ocr}, Engine: {ocr_engine})")
            if not Path(input_path).exists():
                return False, "Input file does not exist."

            doc = fitz.open(input_path)
            total_pages = len(doc)
            logger.info(f"📂 [LOAD] PDF opened successfully. Total pages: {total_pages}")
            
            if total_pages == 0:
                return False, "PDF is empty."

            if mode == 'text_clean':
                res = self._process_text_clean(doc, output_path, text_to_remove)
            else:
                res = self._process_image_bleach_parallel(doc, output_path, input_path, text_to_remove, 
                                                         do_redaction, do_header_clean, do_ocr, ocr_engine, progress_callback)
            
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"✅ [FINISH] Total processing time: {duration:.2f}s | Avg: {duration/total_pages:.2f}s/page")
            return res
        except Exception as e:
            logger.error(f"❌ [CRITICAL ERROR] {str(e)}", exc_info=True)
            return False, f"Internal Error: {str(e)}"
        finally:
            if doc: doc.close()

    def _process_image_bleach_parallel(self, doc: fitz.Document, output_path: str, input_path: str, 
                                      text_to_remove: str = "", do_redaction: bool = True, 
                                      do_header_clean: bool = True, do_ocr: bool = False, 
                                      ocr_engine: str = "easyocr", progress_callback=None) -> Tuple[bool, str]:
        """
        UPGRADED: Parallelized page processing with performance monitoring.
        """
        # Step 1: Optional Redaction
        if do_redaction:
            redact_start = time.time()
            if progress_callback: progress_callback("正在精准擦除文本对象...", 5)
            phrases = [p.strip() for p in text_to_remove.replace('，', ',').split(',') if p.strip()]
            common_patterns = ["知识星球", "VX:", "FCCNN88", "Evaluation Only"]
            all_phrases = list(set(phrases + common_patterns))

            for page in doc:
                for phrase in all_phrases:
                    for inst in page.search_for(phrase):
                        page.add_redact_annot(inst, fill=(1, 1, 1))
                page.apply_redactions()
            logger.info(f"✂️ [REDACT] Completed in {time.time() - redact_start:.2f}s")

        # Step 2: Prepare page rendering tasks
        total_pages = len(doc)
        tasks = []
        render_start_total = time.time()
        
        dpi = 200 
        for i in range(total_pages):
            page = doc[i]
            pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB)
            has_native_text = len(page.get_text().strip()) > 0
            tasks.append((i, pix.tobytes("png"), has_native_text))
            del pix
        logger.info(f"📸 [RENDER] All pages rendered to bytes in {time.time() - render_start_total:.2f}s")

        # Step 3: Run Parallel Workers
        results_map = {}
        # Limit workers for PaddleOCR to avoid OOM on M1 if not careful
        max_workers = min(3 if ocr_engine == "paddleocr" else 4, os.cpu_count() or 1)
        logger.info(f"🔥 [PARALLEL] Dispatching {total_pages} pages to {max_workers} workers (Engine: {ocr_engine})...")
        
        with ProcessPoolExecutor(max_workers=max_workers, initializer=_init_worker_ocr, 
                                 initargs=(['ch_sim', 'en'], ocr_engine)) as executor:
            future_to_index = {
                executor.submit(_process_page_parallel, idx, img_data, self.threshold, 
                               do_header_clean, (do_ocr and has_text), ocr_engine): idx 
                for idx, img_data, has_text in tasks
            }
            
            completed_count = 0
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    res = future.result()
                    results_map[idx] = res
                    completed_count += 1
                    
                    if progress_callback:
                        percent = 10 + int((completed_count / total_pages) * 80)
                        progress_callback(f"处理中... {completed_count}/{total_pages}", percent)
                    
                    m = res.get('metrics', {})
                    logger.info(f"📝 [PAGE] {idx+1}/{total_pages} | Bleach: {m.get('bleach',0):.2f}s | OCR: {m.get('ocr',0):.2f}s | WorkerTotal: {m.get('total',0):.2f}s")
                except Exception as e:
                    logger.error(f"❌ [WORKER ERROR] Page {idx+1} failed: {e}")

        # Step 4: Reassemble PDF
        if not results_map:
            return False, "All worker tasks failed."

        if progress_callback: progress_callback("正在封装最终文档...", 92)
        assembly_start = time.time()
        out_doc = fitz.open()
        
        for i in range(total_pages):
            if i not in results_map or not results_map[i]['success']:
                logger.warning(f"⚠️ Page {i+1} missing or failed, inserting blank page.")
                out_doc.new_page()
                continue
                
            res = results_map[i]
            w, h = res['dimensions']
            new_page = out_doc.new_page(width=w, height=h)
            
            # Insert Image
            new_page.insert_image(fitz.Rect(0, 0, w, h), stream=res['img_data'])
            
            # Insert OCR Text
            for text_obj in res.get('ocr_results', []):
                bbox = text_obj['bbox']
                # Both EasyOCR and PaddleOCR now return normalized bbox: [[x,y],...]
                x0, y0 = float(bbox[0][0]), float(bbox[0][1])
                x1, y1 = float(bbox[2][0]), float(bbox[2][1])
                new_page.insert_textbox(fitz.Rect(x0, y0, x1, y1), text_obj['text'], 
                                       fontsize=12, render_mode=3, align=0)
        
        # Save Metadata
        natural_title = Path(input_path).stem
        out_doc.set_metadata({
            "author": "Research Analyst",
            "creator": f"PDF-Engine-v3.3-{ocr_engine}-Parallel(DPI={dpi})",
            "producer": "Secure-Stream-Pro",
            "title": natural_title
        })
        
        out_doc.save(output_path, garbage=4, deflate=True)
        out_doc.close()
        logger.info(f"💾 [SAVE] Assembly & Save completed in {time.time() - assembly_start:.2f}s")
        
        return True, "Success"

    def _process_text_clean(self, doc: fitz.Document, output_path: str, text: str) -> Tuple[bool, str]:
        try:
            phrases = [p.strip() for p in text.replace('，', ',').split(',') if p.strip()]
            for page in doc:
                for phrase in phrases:
                    for inst in page.search_for(phrase):
                        page.add_redact_annot(inst, fill=(1, 1, 1))
                page.apply_redactions()
            doc.save(output_path, garbage=4, deflate=True)
            return True, "Success"
        except Exception as e: return False, str(e)

    def analyze_pdf(self, input_path: str) -> Dict:
        """
        AI Pre-check: Analyzes the PDF to recommend processing parameters.
        """
        res = {
            'mode': 'image_bleach',
            'threshold': 195,
            'do_ocr': True,
            'do_redaction': True,
            'do_header_clean': True,
            'type': 'unknown',
            'details': ''
        }
        doc = None
        try:
            doc = fitz.open(input_path)
            if len(doc) == 0: return res
            
            page = doc[0]
            text = page.get_text().strip()
            text_len = len(text)
            
            # 1. Check if it's a native PDF with lots of text
            if text_len > 300:
                res['type'] = 'native'
                res['do_ocr'] = False # Probably don't need OCR if text is already there
                res['mode'] = 'text_clean'
                res['details'] = f"检测到原生文字层 (约 {text_len} 字)，建议使用文本清理模式。"
                
                # Check for UBS specific keywords in text
                if "UBS" in text or "Global Research" in text:
                    res['threshold'] = 180
                    res['do_header_clean'] = True
                    res['details'] += " 识别为瑞银 (UBS) 风格文档。"
            else:
                # 2. Check for scanned/image-heavy PDF
                res['type'] = 'scanned'
                res['do_ocr'] = True
                res['mode'] = 'image_bleach'
                res['details'] = "文字量较少，判定为扫描件或图片型 PDF，建议开启 OCR。"

            # 3. Color Analysis (Check for Blue Watermarks like UBS)
            pix = page.get_pixmap(dpi=72)
            img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            
            # Focus on header (top 15%)
            header_h = int(pix.h * 0.15)
            header = img_np[0:header_h, :, :]
            
            # Check for blue pixels
            # RGB: R=0, G=1, B=2
            blue_mask = (header[:,:,2] > 230) & (header[:,:,0] < 210) & (header[:,:,1] < 230)
            blue_pixel_ratio = np.sum(blue_mask) / (header.shape[0] * header.shape[1])
            
            if blue_pixel_ratio > 0.005:
                res['threshold'] = 180
                res['do_header_clean'] = True
                res['details'] += " 检测到顶部蓝色调，自动下调阈值至 180 以增强去水印效果。"

            return res
        except Exception as e:
            logger.error(f"Analysis Error: {e}")
            return res
        finally:
            if doc: doc.close()

    def _process_image_opencv(self, img_bytes: bytes, do_header_clean: bool = True) -> Tuple[bool, Optional[np.ndarray]]:
        try:
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None: return False, None

            # 1. Targeted Bleaching
            _, thresh = cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), self.threshold, 255, cv2.THRESH_BINARY)
            img[thresh == 255] = [255, 255, 255]

            # 2. Header Cleaning
            if do_header_clean:
                h, w = img.shape[:2]
                header_h = int(h * 0.08)
                header_area = img[0:header_h, :]
                header_gray = cv2.cvtColor(header_area, cv2.COLOR_BGR2GRAY)
                header_mask = cv2.threshold(header_gray, 150, 255, cv2.THRESH_BINARY)[1]
                header_area[header_mask == 255] = [255, 255, 255]
                blue_mask = (header_area[:,:,0] > 150) & (header_area[:,:,1] < 150) & (header_area[:,:,2] < 150)
                header_area[blue_mask] = [255, 255, 255]

            return True, img
        except Exception as e:
            logger.error(f"OpenCV error: {e}")
            return False, None
