import pypdf
from reportlab.pdfgen import canvas
import os

def create_dummy_pdf(filename):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "Hello World")
    c.save()

def test_pypdf():
    filename = "test_pypdf.pdf"
    create_dummy_pdf(filename)
    
    try:
        reader = pypdf.PdfReader(filename)
        page = reader.pages[0]
        text = page.extract_text()
        print(f"Extracted text: '{text.strip()}'")
        
        if "Hello World" in text:
            print("SUCCESS: pypdf is working correctly.")
        else:
            print("FAILURE: pypdf did not extract expected text.")
            
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_pypdf()
