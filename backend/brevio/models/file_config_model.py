from typing import Optional
from pydantic import BaseModel

class FileConfig(BaseModel):
    transcription_path: Optional[str] = None
    pdf_path: Optional[str] = None
    document_path: Optional[str] = None
    summary_path: Optional[str] = None