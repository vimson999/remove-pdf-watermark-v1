import easyocr
import torch
import numpy as np

# Test if Reader uses MPS
reader = easyocr.Reader(['ch_sim', 'en'], gpu=True)
device = next(reader.detector.parameters()).device
print(f"Device: {device}")
