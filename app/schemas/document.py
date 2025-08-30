from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.document import DocumentStatus

class DocumentBase(BaseModel):
    filename: str
    original_filename: str
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    status: DocumentStatus
    ocr_text: Optional[str] = None
    structured_content: Optional[Dict[str, Any]] = None
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
