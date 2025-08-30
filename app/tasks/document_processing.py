import fitz  # PyMuPDF
from PIL import Image
import io
import json
from typing import Dict, Any
from celery import current_task

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.services.storage_service import storage_service

@celery_app.task(bind=True)
def process_document_task(self, document_id: int):
    """处理文档的异步任务"""
    db = SessionLocal()
    
    try:
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            current_task.update_state(state='FAILURE', meta={'error': 'Document not found'})
            return
        
        # Update status to processing
        document.status = DocumentStatus.PROCESSING
        db.commit()
        
        # Download file from storage service
        try:
            import asyncio
            file_content = asyncio.run(storage_service.get_file(document.file_path))
            if file_content is None:
                raise Exception(f"File not found: {document.file_path}")
        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.processing_error = f"Failed to download file: {str(e)}"
            db.commit()
            current_task.update_state(state='FAILURE', meta={'error': str(e)})
            return
        
        # Process based on file type
        if document.mime_type == 'application/pdf':
            result = process_pdf(file_content)
        elif document.mime_type.startswith('image/'):
            result = process_image(file_content)
        else:
            document.status = DocumentStatus.FAILED
            document.processing_error = f"Unsupported file type: {document.mime_type}"
            db.commit()
            current_task.update_state(state='FAILURE', meta={'error': 'Unsupported file type'})
            return
        
        if result['success']:
            document.ocr_text = result.get('text', '')
            document.structured_content = result.get('structured_content', {})
            document.status = DocumentStatus.STRUCTURED
        else:
            document.status = DocumentStatus.FAILED
            document.processing_error = result.get('error', 'Processing failed')
        
        db.commit()
        current_task.update_state(state='SUCCESS')
        
    except Exception as e:
        if document:
            document.status = DocumentStatus.FAILED
            document.processing_error = str(e)
            db.commit()
        current_task.update_state(state='FAILURE', meta={'error': str(e)})
    finally:
        db.close()

def process_pdf(file_content: bytes) -> Dict[str, Any]:
    """处理PDF文件"""
    try:
        # Open PDF with PyMuPDF
        pdf_document = fitz.open(stream=file_content, filetype="pdf")
        
        text_content = ""
        structured_content = {
            "pages": [],
            "metadata": {
                "page_count": len(pdf_document),
                "title": pdf_document.metadata.get("title", ""),
                "author": pdf_document.metadata.get("author", ""),
                "subject": pdf_document.metadata.get("subject", "")
            }
        }
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Extract text
            page_text = page.get_text()
            text_content += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            # Extract images (basic)
            image_list = page.get_images()
            page_info = {
                "page_number": page_num + 1,
                "text": page_text,
                "images": len(image_list)
            }
            
            structured_content["pages"].append(page_info)
        
        pdf_document.close()
        
        return {
            "success": True,
            "text": text_content,
            "structured_content": structured_content
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"PDF processing failed: {str(e)}"
        }

def process_image(file_content: bytes) -> Dict[str, Any]:
    """处理图片文件（OCR）"""
    try:
        # For MVP, we'll use basic text extraction
        # In production, integrate with AWS Textract or similar OCR service
        
        # Convert to PIL Image for basic processing
        image = Image.open(io.BytesIO(file_content))
        
        # Basic image info
        structured_content = {
            "image_info": {
                "format": image.format,
                "mode": image.mode,
                "size": image.size,
                "width": image.width,
                "height": image.height
            }
        }
        
        # For now, return basic structure
        # TODO: Integrate with OCR service
        return {
            "success": True,
            "text": "",  # OCR text would go here
            "structured_content": structured_content
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Image processing failed: {str(e)}"
        }
