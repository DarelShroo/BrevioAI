
import asyncio
import logging
import os
import sys

# Add /app to sys.path if not there
sys.path.append("/app")

from core.brevio.managers.directory_manager import DirectoryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    manager = DirectoryManager()
    
    # We test SBD02 specifically as it failed before (now requires OCR)
    target_file = "data/temp_uploads/172fdd4e-6a9f-4d60-9bc0-e081dbc1dc41_SBD02_Contenidos.pdf"
    
    # Also verify tesseract installation
    try:
        import pytesseract
        logger.info(f"Pytesseract version: {pytesseract.get_tesseract_version()}")
    except Exception as e:
        logger.error(f"Failed to check tesseract version: {e}")

    if not os.path.exists(target_file):
        print(f"File {target_file} not found")
        # Try to find it via listing
        base_dir = "data/temp_uploads"
        files = [f for f in os.listdir(base_dir) if f.lower().endswith(".pdf")]
        for f in files:
            if "SBD02" in f:
                target_file = os.path.join(base_dir, f)
                break
    
    logger.info(f"Testing {target_file}")
    
    try:
        fragments = await manager.read_pdf(target_file, None)
        logger.info(f"SUCCESS: Extracted {len(fragments)} fragments via OCR/Text")
        if fragments:
            logger.info(f"Sample text: {fragments[0][:100]}...")
    except Exception as e:
        logger.error(f"FAILURE: {e}")

if __name__ == "__main__":
    asyncio.run(main())
