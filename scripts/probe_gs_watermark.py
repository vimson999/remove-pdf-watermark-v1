import fitz
import sys

def probe_watermark_structure(pdf_path, search_text="前沿收录"):
    doc = fitz.open(pdf_path)
    found_text = False
    
    print(f"🔍 Probing PDF structure for: {pdf_path}")
    
    for i in range(len(doc)):
        page = doc[i]
        # 1. Search for text objects
        text_instances = page.search_for(search_text)
        if text_instances:
            print(f"📍 Page {i+1}: Found '{search_text}' as TEXT objects at {text_instances}")
            found_text = True
            
        # 2. Check for images (just count)
        img_list = page.get_images()
        if i == 0:
            print(f"🖼️ Page {i+1}: Contains {len(img_list)} images.")
            
    doc.close()
    if not found_text:
        print(f"❓ '{search_text}' was NOT found as a standard text object. It might be an IMAGE or VECTOR.")

if __name__ == "__main__":
    probe_watermark_structure("samples/260303-GS-MiniMax集团（0100.HK）2025财年四季度业绩初评.pdf")
