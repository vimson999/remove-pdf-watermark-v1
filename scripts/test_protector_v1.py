import os
import sys
import fitz
# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pdf_protector import PDFProtector

def test_single_protection():
    input_pdf = "samples/test_small_6pages.pdf"
    output_pdf = "samples/outputs/test_protected_v1.pdf"
    watermark_text = "INTERNAL ONLY - DO NOT COPY"
    
    if not os.path.exists("samples/outputs"):
        os.makedirs("samples/outputs")

    print(f"🚀 Starting protection test for: {input_pdf}")
    
    # 1. Apply protection
    success, result = PDFProtector.add_watermark_and_protect(
        input_pdf, 
        output_pdf, 
        watermark_text=watermark_text,
        owner_pw="MY_SECRET_OWNER_KEY"
    )
    
    if success:
        print(f"✅ Protection applied successfully. Output: {output_pdf}")
        print(f"🔑 Owner Password (fixed for test): {result}")
        
        # 2. Verification
        print("\n🔍 Verifying results...")
        doc = fitz.open(output_pdf)
        
        # Check if encrypted
        is_encrypted = doc.is_encrypted
        print(f"- Is Encrypted: {is_encrypted}")
        
        # Check Permissions
        # PDF_PERM_PRINT = 4, PDF_PERM_COPY = 16, etc.
        # We only allowed ACCESSIBILITY (reading).
        permissions = doc.permissions
        print(f"- Permissions (Integer): {permissions}")
        
        # In PyMuPDF, checking specific permissions:
        can_print = permissions & fitz.PDF_PERM_PRINT
        can_copy = permissions & fitz.PDF_PERM_COPY
        
        print(f"- Can Print: {'YES (ERROR)' if can_print else 'NO (SUCCESS)'}")
        print(f"- Can Copy: {'YES (ERROR)' if can_copy else 'NO (SUCCESS)'}")
        
        doc.close()
        print("\n🎉 Test completed. Please manually check the PDF in 'samples/outputs/test_protected_v1.pdf' for visual watermark.")
    else:
        print(f"❌ Protection failed: {result}")

if __name__ == "__main__":
    test_single_protection()
