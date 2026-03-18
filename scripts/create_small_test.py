import fitz

def create_pdf(filename, pages=6):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        # Main content
        page.insert_text((72, 72), f"This is the main content of page {i+1}", fontsize=14)
        page.insert_text((72, 100), "Financial Report Analysis 2026", fontsize=12)
        
        # Simulated watermark (light grey)
        # Simplified: no rotation to avoid more errors for now
        for j in range(2):
            page.insert_text((100, 200 + j*300), "知识星球：内部资料", fontsize=40, color=(0.9, 0.9, 0.9))
            page.insert_text((100, 250 + j*300), "VX: FCCNN88", fontsize=30, color=(0.95, 0.95, 0.95))
            
    doc.save(filename)
    doc.close()
    print(f"Created test PDF: {filename} ({pages} pages)")

if __name__ == "__main__":
    create_pdf("test_small_6pages.pdf", 6)
