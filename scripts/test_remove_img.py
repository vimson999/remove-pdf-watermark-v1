import fitz
doc = fitz.open("瑞银-中国中免（601888）我们仍看好公司增长前景.pdf")
page = doc[0]
img_list = page.get_images()
if img_list:
    xref = img_list[0][0]
    # Redact the image area? No, that deletes the text too if it's over it.
    # Let's try to just remove the image object.
    # Actually, if the image is the background, we can try to bleach it.
    pass
doc.close()
