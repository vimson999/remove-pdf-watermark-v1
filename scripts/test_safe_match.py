import cv2
import numpy as np
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_template_wipe(img: np.ndarray) -> np.ndarray:
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    templates = [
        "app/resources/watermarks/water-1.png",
        "app/resources/watermarks/water-2.png",
        "app/resources/watermarks/water-mark-3.png"
    ]
    
    for tmpl_path in templates:
        tmpl = cv2.imread(tmpl_path, cv2.IMREAD_COLOR)
        if tmpl is None:
            continue
            
        h_tmpl, w_tmpl = tmpl.shape[:2]
        gray_tmpl = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
        
        scales = [0.25, 0.3, 0.35, 0.4, 0.5, 0.75, 1.0]
        
        best_val = -1
        best_loc = None
        best_scale = None
        best_h, best_w = 0, 0
        
        for scale in scales:
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
        
        threshold = 0.45 if w_tmpl > h_tmpl * 2 else 0.38
        
        print(f"Template {tmpl_path.split('/')[-1]}: Best val = {best_val} at scale {best_scale}")
        if best_val >= threshold and best_loc is not None:
            print(f"-> Wiping area at {best_loc} with size {best_w}x{best_h}")
            img[best_loc[1]:best_loc[1] + best_h, best_loc[0]:best_loc[0] + best_w] = [255, 255, 255]
            
    return img

if __name__ == "__main__":
    img = cv2.imread('debug_p2_raw.png')
    
    # Simulate the pipeline: bleach then template wipe
    # 1. Global Bleach
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh_img = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)
    img[thresh_img == 255] = [255, 255, 255]
    
    # 2. Template wipe
    img = apply_template_wipe(img)
    
    cv2.imwrite('debug_p2_safe.png', img)
    print("Done. Check debug_p2_safe.png")
