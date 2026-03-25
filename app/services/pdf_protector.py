import fitz
import os
import logging
import uuid
import random

logger = logging.getLogger(__name__)

class PDFProtector:
    """
    V3 Service with Adversarial Watermarking:
    - Random Character-level Jitter (Breaks OCR and template matching).
    - Multi-variant Rotation & Sizing.
    - Ghosting layers (Adds background noise for inpainting).
    - AES-256 Lockdown.
    """

    @staticmethod
    def add_watermark_and_protect(input_path, output_path, watermark_text="请您不要外传", owner_pw=None):
        if not owner_pw:
            owner_pw = str(uuid.uuid4())
        
        try:
            doc = fitz.open(input_path)
            
            for page in doc:
                rect = page.rect
                width, height = rect.width, rect.height
                
                # 1. Main Adversarial Watermark (Centered with High Entropy)
                # We split text into characters to apply individual jitter
                chars = list(watermark_text)
                base_fontsize = random.randint(50, 68)
                base_angle = random.randint(35, 55)
                base_opacity = random.uniform(0.18, 0.32)
                
                # Center point with jitter
                cx, cy = width/2 + random.randint(-20, 20), height/2 + random.randint(-20, 20)
                
                for i, char in enumerate(chars):
                    # Randomize each character's properties slightly
                    char_size = base_fontsize + random.randint(-5, 5)
                    char_offset = i * (char_size * 0.85) + random.randint(-10, 10)
                    
                    # Apply rotation matrix per character
                    matrix = fitz.Matrix(base_angle)
                    point = fitz.Point(cx - (len(chars)*char_size/4) + char_offset, cy)
                    
                    # Ghosting Layer (Slightly offset, very faint)
                    page.insert_text(
                        point=point + (2, 2),
                        text=char,
                        fontsize=char_size,
                        fontname="china-ss",
                        color=(0.8, 0.8, 0.8),
                        fill_opacity=0.1,
                        morph=(point, matrix)
                    )
                    
                    # Main Layer
                    page.insert_text(
                        point=point,
                        text=char,
                        fontsize=char_size,
                        fontname="china-ss",
                        color=(0.5, 0.5, 0.5),
                        fill_opacity=base_opacity,
                        morph=(point, matrix)
                    )
                
                # 2. Strategic Tiled Protection (Smaller, varying angles)
                tiled_positions = [
                    (80, 120), (width - 150, 150), (80, height - 150)
                ]
                for tx, ty in tiled_positions:
                    t_size = random.randint(18, 26)
                    t_angle = random.randint(0, 360) # Full rotation for tiles
                    t_point = fitz.Point(tx + random.randint(-15, 15), ty + random.randint(-15, 15))
                    page.insert_text(
                        point=t_point,
                        text=watermark_text,
                        fontsize=t_size,
                        fontname="china-ss",
                        color=(0.6, 0.6, 0.6),
                        fill_opacity=0.25,
                        morph=(t_point, fitz.Matrix(t_angle))
                    )

            # 3. Permissions Lockdown
            perm = int(fitz.PDF_PERM_ACCESSIBILITY)
            doc.save(
                output_path,
                encryption=fitz.PDF_ENCRYPT_AES_256,
                owner_pw=owner_pw,
                user_pw=None,
                permissions=perm,
                garbage=2,
                deflate=True
            )
            doc.close()
            return True, owner_pw
            
        except Exception as e:
            logger.error(f"V3 Protection failed: {str(e)}")
            return False, str(e)

if __name__ == "__main__":
    # Quick internal test if run directly
    pass
