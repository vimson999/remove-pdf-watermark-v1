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

# --- Template Matching for Persistent Watermarks ---

_watermark_templates: List[Dict] = []
_custom_qr: Optional[np.ndarray] = None

def _load_templates():
    global _watermark_templates
    if not _watermark_templates:
        # Determine resource path relative to this file (app/services/pdf_processor.py)
        # app/services/../../app/resources/watermarks
        base_dir = os.path.dirname(os.path.dirname(__file__))
        resource_dir = os.path.join(base_dir, "resources", "watermarks")
        
        possible_templates = ["water-1.png", "water-2.png", "water-mark-3.png"]
        for name in possible_templates:
            tmpl_path = os.path.join(resource_dir, name)
            if os.path.exists(tmpl_path):
                tmpl = cv2.imread(tmpl_path, cv2.IMREAD_COLOR)
                if tmpl is not None:
                    _watermark_templates.append({"name": name, "img": tmpl})
                    logger.info(f"Loaded watermark template: {name} from {resource_dir}")
            else:
                # Fallback to root for legacy support or local testing
                if os.path.exists(name):
                    tmpl = cv2.imread(name, cv2.IMREAD_COLOR)
                    if tmpl is not None:
                        _watermark_templates.append({"name": name, "img": tmpl})
                        logger.info(f"Loaded watermark template: {name} from root")
    return _watermark_templates

def _load_custom_qr() -> Optional[np.ndarray]:
    global _custom_qr
    if _custom_qr is None:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        custom_qr_path = os.path.join(base_dir, "resources", "watermarks", "my_wechat_qr.png")
        if os.path.exists(custom_qr_path):
            _custom_qr = cv2.imread(custom_qr_path, cv2.IMREAD_COLOR)
    return _custom_qr

def _paste_custom_qr(img: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> None:
    custom_qr = _load_custom_qr()
    if custom_qr is None:
        return

    target_w = x2 - x1
    target_h = y2 - y1
    if target_w <= 0 or target_h <= 0:
        return

    qr_h, qr_w = custom_qr.shape[:2]
    scale = min(target_w / qr_w, target_h / qr_h)
    if scale <= 0:
        return

    paste_w = max(1, min(target_w, int(qr_w * scale)))
    paste_h = max(1, min(target_h, int(qr_h * scale)))
    resized_qr = cv2.resize(custom_qr, (paste_w, paste_h), interpolation=cv2.INTER_AREA)
    offset_x = x1 + (target_w - paste_w) // 2
    offset_y = y1 + (target_h - paste_h) // 2
    img[offset_y:offset_y + paste_h, offset_x:offset_x + paste_w] = resized_qr

def apply_template_wipe(img: np.ndarray) -> np.ndarray:
    """Find and wipe known watermark templates using multi-scale template matching."""
    templates = _load_templates()
    if not templates:
        return img
        
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    for tmpl_data in templates:
        try:
            tmpl_name = tmpl_data["name"]
            tmpl = tmpl_data["img"]
            
            h_tmpl, w_tmpl = tmpl.shape[:2]
            gray_tmpl = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
            
            # Multi-scale matching
            scales = [0.25, 0.3, 0.35, 0.4, 0.5, 0.75, 1.0]
            
            best_val = -1
            best_loc = None
            best_scale = None
            best_h, best_w = 0, 0
            
            for scale in scales:
                # Use fx and fy to avoid rounding distortions
                t = cv2.resize(gray_tmpl, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                curr_h, curr_w = t.shape[:2]
                
                if curr_h > img.shape[0] or curr_w > img.shape[1] or curr_h < 10 or curr_w < 10:
                    continue
                    
                res = cv2.matchTemplate(gray_img, t, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                if max_val > best_val:
                    best_val = max_val
                    best_loc = max_loc
                    best_scale = scale
                    best_h, best_w = curr_h, curr_w
            
            # Safe threshold logic
            # Lowering the threshold to 0.32 for QR codes because PDF rendering artifacts
            # at 200 DPI can occasionally chop off the top of the original QR code,
            # drastically reducing the match score. 0.32 is still well above the noise floor (~0.15).
            threshold = 0.45 if w_tmpl > h_tmpl * 2 else 0.32
            
            if best_val >= threshold and best_loc is not None:
                # The matched size might be slightly smaller than the actual rendered QR code.
                # If we don't obliterate the outer 'finder patterns' of the old QR code,
                # scanners will still read the old one via error correction!
                # We expand the bounding box by 20% on ALL sides (1.4x total size).
                is_qr_template = tmpl_name in ["water-1.png", "water-mark-3.png"]
                margin_w = int(best_w * 0.20)
                margin_h = int(best_h * 0.20)
                
                wipe_x1 = max(0, best_loc[0] - margin_w)
                wipe_y1 = max(0, best_loc[1] - margin_h)
                wipe_x2 = min(img.shape[1], best_loc[0] + best_w + margin_w)
                wipe_y2 = min(img.shape[0], best_loc[1] + best_h + margin_h)
                if is_qr_template:
                    wipe_y2 = min(img.shape[0], best_loc[1] + best_h + int(best_h * 0.75))
                
                box_w = wipe_x2 - wipe_x1
                box_h = wipe_y2 - wipe_y1
                
                if box_w <= 0 or box_h <= 0:
                    continue
                
                # Wipe the expanded area to pure white.
                img[wipe_y1:wipe_y2, wipe_x1:wipe_x2] = [255, 255, 255]
                if is_qr_template:
                    qr_y2 = min(img.shape[0], best_loc[1] + best_h + margin_h)
                    _paste_custom_qr(img, wipe_x1, wipe_y1, wipe_x2, qr_y2)

        except Exception as e:
            logger.error(f"Template matching failed: {e}")
    return img

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

def apply_lower_left_watermark_clean(img: np.ndarray) -> np.ndarray:
    """Remove compact QR/logo artifacts that appear in the lower-left page footer."""
    h, w = img.shape[:2]
    y_start = int(h * 0.72)
    x_end = int(w * 0.36)
    roi = img[y_start:h, 0:x_end]
    if roi.size == 0:
        return img

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    dark_mask = (gray < 150).astype(np.uint8) * 255
    dark_mask = cv2.dilate(dark_mask, np.ones((3, 3), np.uint8), iterations=1)

    components, labels, stats, _ = cv2.connectedComponentsWithStats(dark_mask, connectivity=8)
    for label in range(1, components):
        x, y, comp_w, comp_h, area = stats[label]
        abs_y = y_start + y
        if area <= 0:
            continue
        aspect = comp_w / max(comp_h, 1)
        is_footer_square = (
            abs_y > int(h * 0.86) and
            x < int(w * 0.18) and
            35 <= comp_w <= int(w * 0.12) and
            35 <= comp_h <= int(h * 0.12) and
            0.70 <= aspect <= 1.35 and
            area >= 700
        )
        if is_footer_square:
            pad = max(6, int(max(comp_w, comp_h) * 0.08))
            x1 = max(0, x - pad)
            y1 = max(0, y_start + y - pad)
            x2 = min(w, x + comp_w + pad)
            qr_y2 = min(h, y_start + y + comp_h + pad)
            wipe_y2 = min(h, y_start + y + comp_h + int(comp_h * 0.55))
            img[y1:wipe_y2, x1:x2] = [255, 255, 255]
            _paste_custom_qr(img, x1, y1, x2, qr_y2)

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    color_mask = ((saturation > 45) & (value < 245)).astype(np.uint8) * 255
    color_mask = cv2.dilate(color_mask, np.ones((3, 3), np.uint8), iterations=1)

    components, labels, stats, _ = cv2.connectedComponentsWithStats(color_mask, connectivity=8)
    for label in range(1, components):
        x, y, comp_w, comp_h, area = stats[label]
        abs_y = y_start + y
        if area <= 0:
            continue
        is_footer_logo = (
            abs_y > int(h * 0.93) and
            x < int(w * 0.09) and
            18 <= comp_w <= int(w * 0.09) and
            8 <= comp_h <= int(h * 0.06) and
            area <= 3000
        )
        if is_footer_logo:
            pad = 8
            x1 = max(0, x - pad)
            y1 = max(0, y_start + y - pad)
            x2 = min(w, x + comp_w + pad)
            y2 = min(h, y_start + y + comp_h + pad)
            img[y1:y2, x1:x2] = [255, 255, 255]

    return img

def apply_ms_side_clean(img: np.ndarray) -> np.ndarray:
    """Morgan Stanley specific: Vertical side bars or disclaimer text."""
    h, w = img.shape[:2]
    # Erase left vertical 5% and right vertical 5%
    img[:, 0 : int(w * 0.05)] = [255, 255, 255]
    img[:, int(w * 0.95) : w] = [255, 255, 255]
    return img

def apply_nomura_header_strip(img: np.ndarray) -> np.ndarray:
    """Nomura specific: Horizontal lines in header."""
    h, w = img.shape[:2]
    # More aggressive header wipe for Nomura (top 12%)
    img[0 : int(h * 0.12), :] = [255, 255, 255]
    return img

def _bleach_image(img: np.ndarray, threshold: int, do_header_clean: bool, 
                  institution: str = "unknown") -> Tuple[np.ndarray, float]:
    start = time.time()
    
    # 1. Global Bleach
    img = apply_global_bleach(img, threshold)
    
    # 2. Template Matching Wipe (New!)
    img = apply_template_wipe(img)
    img = apply_lower_left_watermark_clean(img)
    
    # 3. Institution-Specific Wipes
    if institution == "ms":
        img = apply_ms_side_clean(img)
    elif institution == "nomura":
        img = apply_nomura_header_strip(img)
    
    # 4. Common Wipes
    if do_header_clean and institution != "nomura": # Nomura handled above
        img = apply_header_clean(img)
    
    img = apply_footer_wipe(img)
    
    return img, time.time() - start

def _process_page_parallel(page_index: int, img_bytes: bytes, threshold: int, 
                          do_header_clean: bool, do_ocr: bool, ocr_engine: str = "easyocr",
                          institution: str = "unknown", orig_dimensions: Tuple[float, float] = (0, 0)) -> Dict:
    start_time = time.time()
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return {'index': page_index, 'success': False, 'error': 'Image decode failed'}

    # 1. Bleach with Institution context
    img, bleach_duration = _bleach_image(img, threshold, do_header_clean, institution)

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
        'pixel_dimensions': (img.shape[1], img.shape[0]),
        'orig_dimensions': orig_dimensions
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

            # Auto-detect Institution
            analysis = self.analyze_pdf(input_path)
            institution = analysis.get('institution', 'unknown')
            threshold = analysis.get('threshold', self.threshold)

            doc = fitz.open(input_path)
            total_pages = len(doc)
            
            if mode == 'text_clean' and analysis['type'] == 'native':
                res = self._process_text_clean(doc, output_path, text_to_remove)
            else:
                res = self._process_image_bleach_parallel(doc, output_path, input_path, text_to_remove, 
                                                         do_redaction, do_header_clean, do_ocr, ocr_engine, 
                                                         progress_callback, institution, threshold)
            
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
                                      ocr_engine: str = "easyocr", progress_callback=None,
                                      institution: str = "unknown", threshold: int = 195) -> Tuple[bool, str]:
        if do_redaction:
            if progress_callback: progress_callback("正在精准擦除文本对象...", 5)
            phrases = [p.strip() for p in text_to_remove.replace('，', ',').split(',') if p.strip()]
            common_patterns = ["知识星球", "VX:", "FCCNN88", "Evaluation Only", "西湖有鱼快来吃", "前沿信息收录", "一等研报"]
            all_phrases = list(set(phrases + common_patterns))
            for page in doc:
                for phrase in all_phrases:
                    for inst in page.search_for(phrase):
                        page.add_redact_annot(inst, fill=(1, 1, 1))
                page.apply_redactions()

        total_pages = len(doc)
        tasks = []
        
        # Adaptive DPI logic
        MAX_SAFE_PIXELS = 3500
        DEFAULT_DPI = 200
        
        for i in range(total_pages):
            page = doc[i]
            rect = page.rect
            orig_w, orig_h = rect.width, rect.height
            orig_max_dim = max(orig_w, orig_h)
            projected_pixels = orig_max_dim * (DEFAULT_DPI / 72)
            
            if projected_pixels > MAX_SAFE_PIXELS:
                dpi = max(120, int((MAX_SAFE_PIXELS * 72) / orig_max_dim))
            else:
                dpi = DEFAULT_DPI

            pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB)
            has_native_text = len(page.get_text().strip()) > 0
            tasks.append((i, pix.tobytes("png"), has_native_text, (orig_w, orig_h)))
            del pix

        results_map = {}
        max_workers = min(3 if ocr_engine == "paddleocr" else 4, os.cpu_count() or 1)
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(_process_page_parallel, idx, img_data, threshold, 
                               do_header_clean, (do_ocr and has_text), ocr_engine, institution, orig_dims): idx 
                for idx, img_data, has_text, orig_dims in tasks
            }
            
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    res = future.result()
                    results_map[idx] = res
                    if progress_callback:
                        percent = 10 + int((len(results_map) / total_pages) * 80)
                        progress_callback(f"处理中... {len(results_map)}/{total_pages}", percent)
                except Exception as e:
                    logger.error(f"❌ [WORKER ERROR] Page {idx+1} failed: {e}")

        if not results_map: return False, "All tasks failed."

        if progress_callback: progress_callback("正在封装最终文档...", 92)
        out_doc = fitz.open()
        for i in range(total_pages):
            if i not in results_map: continue
            res = results_map[i]
            pw, ph = res['pixel_dimensions']
            ow, oh = res['orig_dimensions']
            
            new_page = out_doc.new_page(width=ow, height=oh)
            new_page.insert_image(fitz.Rect(0, 0, ow, oh), stream=res['img_data'])
            
            # Scale factor from Pixels to Points
            scale_x = ow / pw
            scale_y = oh / ph
            
            for text_obj in res.get('ocr_results', []):
                bbox = text_obj['bbox']
                # bbox is [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
                point_rect = fitz.Rect(
                    bbox[0][0] * scale_x, 
                    bbox[0][1] * scale_y, 
                    bbox[2][0] * scale_x, 
                    bbox[2][1] * scale_y
                )
                new_page.insert_textbox(point_rect, text_obj['text'], fontsize=11, render_mode=3)
        
        out_doc.save(output_path, garbage=4, deflate=True)
        out_doc.close()
        return True, "Success"

    def analyze_pdf(self, input_path: str) -> Dict:
        res = {'mode': 'image_bleach', 'threshold': 195, 'do_ocr': True, 'do_redaction': True, 
               'do_header_clean': True, 'type': 'unknown', 'institution': 'unknown', 'details': ''}
        doc = None
        try:
            doc = fitz.open(input_path)
            if len(doc) == 0: return res
            
            first_page_text = doc[0].get_text()
            text_lower = first_page_text.lower()
            
            # Text-based detection
            if "morgan stanley" in text_lower or "摩根士丹利" in text_lower:
                res['institution'] = 'ms'
                res['threshold'] = 195 # MS watermarks usually fade with 195
            elif "nomura" in text_lower or "野村" in text_lower:
                res['institution'] = 'nomura'
                res['threshold'] = 190 # Nomura's faint lines need a lower threshold
            elif "ubs" in text_lower or "瑞银" in text_lower:
                res['institution'] = 'ubs'
                res['threshold'] = 180
            
            if len(first_page_text.strip()) > 300:
                res.update({'type': 'native', 'do_ocr': False, 'mode': 'text_clean', 'details': '检测到原生文字层。'})
            else:
                res.update({'type': 'scanned', 'do_ocr': True, 'details': '判定为扫描件。'})
            
            # Color analysis for specific watermarks
            pix = doc[0].get_pixmap(dpi=72)
            img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            header = img_np[0:int(pix.h * 0.15), :, :]
            blue_mask = (header[:,:,2] > 230) & (header[:,:,0] < 210)
            
            if np.sum(blue_mask) / (header.shape[0] * header.shape[1]) > 0.005:
                if res['institution'] == 'unknown':
                    res['institution'] = 'ubs' # Common fallback
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
