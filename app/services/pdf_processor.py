import fitz  # type: ignore
import cv2
import numpy as np
import logging
import os
import time
from pathlib import Path
from typing import Tuple, Optional, List, Dict
from concurrent.futures import ProcessPoolExecutor, as_completed
from abc import ABC, abstractmethod

# Configure module-level logger
logger = logging.getLogger(__name__)

# --- Strategy Pattern for OCR Engines ---

class OCRProvider(ABC):
    @abstractmethod
    def read_text(self, img: np.ndarray) -> List[Dict]:
        pass

class EasyOCRProvider(OCRProvider):
    def __init__(self, languages=['ch_sim', 'en']):
        import easyocr
        import torch
        use_gpu = torch.backends.mps.is_available()
        self.reader = easyocr.Reader(languages, gpu=use_gpu)
        self.engine_name = "easyocr"
        logger.info(f"Initialized EasyOCR (MPS: {use_gpu})")

    def read_text(self, img: np.ndarray) -> List[Dict]:
        results = []
        raw_results = self.reader.readtext(img)
        for (bbox, text, prob) in raw_results:
            results.append({'bbox': bbox, 'text': text, 'prob': prob})
        return results

class PaddleOCRProvider(OCRProvider):
    def __init__(self):
        from paddleocr import PaddleOCR
        # PP-OCRv4 mobile is balanced for speed/accuracy on CPU
        # Note: show_log is removed in newer versions of PaddleOCR initialization
        self.reader = PaddleOCR(lang="ch", ocr_version="PP-OCRv4")
        self.engine_name = "paddleocr"
        logger.info("Initialized PaddleOCR (Mobile v4)")

    def read_text(self, img: np.ndarray) -> List[Dict]:
        results = []
        # PaddleOCR 3.4.0+ predict() logic
        raw_results = self.reader.predict(img)
        if raw_results and len(raw_results) > 0:
            res_dict = raw_results[0]
            if isinstance(res_dict, dict) and 'rec_texts' in res_dict:
                texts = res_dict.get('rec_texts', [])
                scores = res_dict.get('rec_scores', [])
                polys = res_dict.get('rec_polys', [])
                for i in range(len(texts)):
                    bbox = polys[i]
                    xs = [p[0] for p in bbox]
                    ys = [p[1] for p in bbox]
                    results.append({
                        'bbox': [[float(min(xs)), float(min(ys))], [float(max(xs)), float(min(ys))], 
                                 [float(max(xs)), float(max(ys))], [float(min(xs)), float(max(ys))]],
                        'text': texts[i],
                        'prob': float(scores[i])
                    })
        return results

# --- Global Resource Holder ---

_current_provider: Optional[OCRProvider] = None

def _get_ocr_provider(engine_type: str) -> Optional[OCRProvider]:
    global _current_provider
    if _current_provider is None or getattr(_current_provider, 'engine_name', '') != engine_type:
        try:
            if engine_type == "paddleocr":
                _current_provider = PaddleOCRProvider()
            else:
                _current_provider = EasyOCRProvider()
        except Exception as e:
            logger.error(f"Failed to initialize OCR Provider {engine_type}: {e}")
            _current_provider = None
    return _current_provider

# --- Core Processing Logic ---

# --- Modular Cleaning Strategies ---

def apply_global_bleach(img: np.ndarray, threshold: int) -> np.ndarray:
    """Standard bleaching for the whole page."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh_img = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    img[thresh_img == 255] = [255, 255, 255]
    return img

def apply_header_clean(img: np.ndarray) -> np.ndarray:
    """Specific logic for top-of-page elements."""
    h, w = img.shape[:2]
    header_h = int(h * 0.08)
    header_area = img[0:header_h, :]
    header_gray = cv2.cvtColor(header_area, cv2.COLOR_BGR2GRAY)
    header_mask = cv2.threshold(header_gray, 180, 255, cv2.THRESH_BINARY)[1]
    header_area[header_mask == 255] = [255, 255, 255]
    return img

def apply_footer_wipe(img: np.ndarray) -> np.ndarray:
    """Targeted physical wipe for bottom-right promotional watermarks."""
    h, w = img.shape[:2]
    # Erase bottom 8%, right 45% (The 'Frontier' zone)
    footer_h = int(h * 0.08)
    footer_w = int(w * 0.45)
    img[h - footer_h : h, w - footer_w : w] = [255, 255, 255]
    return img

def _bleach_image(img: np.ndarray, threshold: int, do_header_clean: bool) -> Tuple[np.ndarray, float]:
    start = time.time()
    
    # 1. Global Bleach (Fundamental)
    img = apply_global_bleach(img, threshold)
    
    # 2. Strategic Wipes
    if do_header_clean:
        img = apply_header_clean(img)
    
    # Always apply footer wipe as it's a common 'nuisance' in current samples
    # In a production version, this would be a toggle: 'do_footer_clean'
    img = apply_footer_wipe(img)
    
    return img, time.time() - start

def _process_page_parallel(page_index: int, img_bytes: bytes, threshold: int, 
                          do_header_clean: bool, do_ocr: bool, ocr_engine: str = "easyocr") -> Dict:
    start_time = time.time()
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return {'index': page_index, 'success': False, 'error': 'Image decode failed'}

    # 1. Bleach
    img, bleach_duration = _bleach_image(img, threshold, do_header_clean)

    # 2. OCR
    ocr_results = []
    ocr_duration = 0
    if do_ocr:
        ocr_start = time.time()
        provider = _get_ocr_provider(ocr_engine)
        if provider:
            try:
                raw_results = provider.read_text(img)
                for res in raw_results:
                    text = res['text']
                    prob = res['prob']
                    if prob < 0.3 or not text.strip(): continue
                    
                    # Filtering logic
                    norm = text.lower().replace(" ", "")
                    if any(p in norm for p in ["知识星球", "vxfccnn88", "evaluationonly", "ripper"]):
                        continue
                    
                    ocr_results.append(res)
            except Exception as e:
                logger.error(f"OCR Error on page {page_index}: {e}")
        ocr_duration = time.time() - ocr_start

    # 3. Encode
    _, buffer = cv2.imencode('.png', img)
    
    return {
        'index': page_index,
        'success': True,
        'img_data': buffer.tobytes(),
        'ocr_results': ocr_results,
        'metrics': {'bleach': bleach_duration, 'ocr': ocr_duration, 'total': time.time() - start_time},
        'dimensions': (img.shape[1], img.shape[0])
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
            logger.info(f"🚀 [START] Processing: {Path(input_path).name} (Engine: {ocr_engine})")
            if not Path(input_path).exists():
                return False, "Input file does not exist."

            doc = fitz.open(input_path)
            total_pages = len(doc)
            
            if mode == 'text_clean':
                res = self._process_text_clean(doc, output_path, text_to_remove)
            else:
                res = self._process_image_bleach_parallel(doc, output_path, input_path, text_to_remove, 
                                                         do_redaction, do_header_clean, do_ocr, ocr_engine, progress_callback)
            
            duration = time.time() - start_time
            logger.info(f"✅ [FINISH] Total time: {duration:.2f}s ({duration/total_pages:.2f}s/page)")
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
        if do_redaction:
            if progress_callback: progress_callback("正在精准擦除文本对象...", 5)
            phrases = [p.strip() for p in text_to_remove.replace('，', ',').split(',') if p.strip()]
            common_patterns = ["知识星球", "VX:", "FCCNN88", "Evaluation Only"]
            all_phrases = list(set(phrases + common_patterns))
            for page in doc:
                for phrase in all_phrases:
                    for inst in page.search_for(phrase):
                        page.add_redact_annot(inst, fill=(1, 1, 1))
                page.apply_redactions()

        total_pages = len(doc)
        tasks = []
        
        # Adaptive DPI logic to prevent pixel explosion on large documents (like UBS)
        # Target: max dimension around 3000-3500px for a good speed/quality balance
        MAX_SAFE_PIXELS = 3500
        DEFAULT_DPI = 200
        
        for i in range(total_pages):
            page = doc[i]
            rect = page.rect
            orig_max_dim = max(rect.width, rect.height) # at 72 DPI
            
            # Calculate what the max dimension would be at 200 DPI
            projected_pixels = orig_max_dim * (DEFAULT_DPI / 72)
            
            if projected_pixels > MAX_SAFE_PIXELS:
                adaptive_dpi = int((MAX_SAFE_PIXELS * 72) / orig_max_dim)
                adaptive_dpi = max(120, adaptive_dpi) # Floor at 120 DPI for OCR quality
                logger.info(f"📏 Page {i+1} is large ({rect.width:.0f}x{rect.height:.0f}), downscaling DPI: {DEFAULT_DPI} -> {adaptive_dpi}")
                dpi = adaptive_dpi
            else:
                dpi = DEFAULT_DPI

            pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB)
            has_native_text = len(page.get_text().strip()) > 0
            tasks.append((i, pix.tobytes("png"), has_native_text))
            del pix

        results_map = {}
        # Strategy: Use fewer workers for heavy OCR to prevent system thrashing
        max_workers = min(3 if ocr_engine == "paddleocr" else 4, os.cpu_count() or 1)
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(_process_page_parallel, idx, img_data, self.threshold, 
                               do_header_clean, (do_ocr and has_text), ocr_engine): idx 
                for idx, img_data, has_text in tasks
            }
            
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    res = future.result()
                    results_map[idx] = res
                    if progress_callback:
                        percent = 10 + int((len(results_map) / total_pages) * 80)
                        progress_callback(f"处理中... {len(results_map)}/{total_pages}", percent)
                    m = res.get('metrics', {})
                    logger.info(f"📝 [PAGE] {idx+1}/{total_pages} | OCR: {m.get('ocr',0):.2f}s | Total: {m.get('total',0):.2f}s")
                except Exception as e:
                    logger.error(f"❌ [WORKER ERROR] Page {idx+1} failed: {e}")

        if not results_map: return False, "All tasks failed."

        if progress_callback: progress_callback("正在封装最终文档...", 92)
        out_doc = fitz.open()
        for i in range(total_pages):
            if i not in results_map: continue
            res = results_map[i]
            w, h = res['dimensions']
            new_page = out_doc.new_page(width=w, height=h)
            new_page.insert_image(fitz.Rect(0, 0, w, h), stream=res['img_data'])
            for text_obj in res.get('ocr_results', []):
                bbox = text_obj['bbox']
                new_page.insert_textbox(fitz.Rect(bbox[0][0], bbox[0][1], bbox[2][0], bbox[2][1]), 
                                       text_obj['text'], fontsize=11, render_mode=3)
        
        out_doc.save(output_path, garbage=4, deflate=True)
        out_doc.close()
        return True, "Success"

    def analyze_pdf(self, input_path: str) -> Dict:
        res = {'mode': 'image_bleach', 'threshold': 195, 'do_ocr': True, 'do_redaction': True, 
               'do_header_clean': True, 'type': 'unknown', 'details': ''}
        doc = None
        try:
            doc = fitz.open(input_path)
            if len(doc) == 0: return res
            text = doc[0].get_text().strip()
            if len(text) > 300:
                res.update({'type': 'native', 'do_ocr': False, 'mode': 'text_clean', 'details': '检测到原生文字层。'})
            else:
                res.update({'type': 'scanned', 'do_ocr': True, 'details': '判定为扫描件。'})
            
            # Color analysis for specific watermarks
            pix = doc[0].get_pixmap(dpi=72)
            img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            header = img_np[0:int(pix.h * 0.15), :, :]
            blue_mask = (header[:,:,2] > 230) & (header[:,:,0] < 210)
            if np.sum(blue_mask) / (header.shape[0] * header.shape[1]) > 0.005:
                res.update({'threshold': 180, 'details': res['details'] + " 识别为瑞银风格，自动优化阈值。"})
            return res
        except Exception as e:
            logger.error(f"Analysis Error: {e}")
            return res
        finally:
            if doc: doc.close()

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

    def split_pdf(self, input_path: str, output_dir: str, step: int = 10) -> List[str]:
        """
        Splits a PDF into multiple files, each containing 'step' pages.
        Returns a list of generated file paths.
        """
        generated_files = []
        doc = None
        try:
            doc = fitz.open(input_path)
            total_pages = len(doc)
            base_name = Path(input_path).stem
            
            for start in range(0, total_pages, step):
                end = min(start + step, total_pages)
                output_filename = f"{base_name}_part_{start//step + 1}.pdf"
                output_path = os.path.join(output_dir, output_filename)
                
                # Create a new document for the segment
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=start, to_page=end-1)
                new_doc.save(output_path, garbage=4, deflate=True)
                new_doc.close()
                
                generated_files.append(output_filename)
                
            return generated_files
        except Exception as e:
            logger.error(f"Split Error: {e}")
            return []
        finally:
            if doc: doc.close()
