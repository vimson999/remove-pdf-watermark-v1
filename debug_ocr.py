import cv2
import numpy as np
import fitz
import easyocr

input_file = "瑞银-中国中免（601888）我们仍看好公司增长前景.pdf"
doc = fitz.open(input_file)
page = doc[0]
pix = page.get_pixmap(dpi=300)
img_data = pix.tobytes("png")

nparr = np.frombuffer(img_data, np.uint8)
img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

# Targeted Bleaching
threshold = 195
_, thresh = cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), threshold, 255, cv2.THRESH_BINARY)
img[thresh == 255] = [255, 255, 255]

# OCR
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
results = reader.readtext(img)

print("OCR Results (Top 20):")
for i, (bbox, text, prob) in enumerate(results[:20]):
    print(f"{i}: {text} (prob: {prob:.2f})")

cv2.imwrite("debug_bleached.png", img)
doc.close()
