from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pathlib import Path
from schemas.document import DatasetDocument, Paragraph
from utils.pdf_reader import PDFReader
import logging
import shutil
import tempfile
import os
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

CUAD_PDF_DIR = Path("../infra/full_contract_pdf")
pdf_reader = PDFReader()

@router.get("/list_documents", response_model=list[DatasetDocument])
def list_documents():
    if not CUAD_PDF_DIR.exists():
        raise HTTPException(status_code=500, detail="Dataset directory not found")

    documents: list[DatasetDocument] = []

    for pdf_path in CUAD_PDF_DIR.rglob("*.pdf"):
        doc = DatasetDocument(
            id=pdf_path.stem, 
            name=pdf_path.name,
            origin='dataset',
            processed=False
        )

        documents.append(doc)
        logger.info(f"Found document in subfolder: {pdf_path.name}")

    return documents


@router.get("/{document_id}/pdf")
def get_document_pdf(document_id: str):
    logger.info(f"Fetching PDF for document ID: {document_id}")
    if not CUAD_PDF_DIR.exists():
         raise HTTPException(status_code=500, detail="Dataset directory not found")
         
    pdf_path = None
    for path in CUAD_PDF_DIR.rglob("*.pdf"):
        if path.stem == document_id:
            pdf_path = path
            break
            
    if not pdf_path:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return FileResponse(path=pdf_path, media_type='application/pdf', filename=pdf_path.name)

@router.post("/process", response_model=list[Paragraph])
async def process_document(
    document_id: str = Form(...),
    file: UploadFile = File(None)
):
    tmp_path = None
    try:
        if file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name
        else:
            pdf_path = None
            for path in CUAD_PDF_DIR.rglob("*.pdf"):
                if path.stem == document_id:
                    pdf_path = path
                    break
            
            if not pdf_path:
                raise HTTPException(status_code=404, detail="Documento no encontrado localmente")
            tmp_path = str(pdf_path)

        df = pdf_reader.PDF_to_dataframe(tmp_path)
        paragraphs = [
            Paragraph(
                id=f"{document_id}_{index}",
                documentId=document_id,
                page=int(row['page']),
                order=int(row['paragraph_enum']),
                text=row.get('clean_text', row['text']),
                bbox=[float(row['x0']), float(row['y0']), float(row['x1']), float(row['y1'])]
            ) for index, row in df.iterrows()
        ]
        return paragraphs

    finally:
        if file and tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.post("/upload", response_model=list[Paragraph])
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
         raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
        
    try:
        df = pdf_reader.PDF_to_dataframe(tmp_path)
        paragraphs = []
        doc_id = "upload_" + uuid.uuid4().hex[:8]
        
        for index, row in df.iterrows():
            paragraphs.append(Paragraph(
                id=f"{doc_id}_{index}",
                documentId=doc_id,
                page=int(row['page']),
                order=int(row['paragraph_enum']),
                text=row['clean_text'] if 'clean_text' in row else row['text'],
                bbox=[float(row['x0']), float(row['y0']), float(row['x1']), float(row['y1'])]
            ))
        return paragraphs
    except Exception as e:
        logger.error(f"Error processing uploaded document: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.get("/")
def document_init():
    return {"message": "Document initialization endpoint"}