from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from schemas.document import DatasetDocument, Paragraph
from schemas.graph import Graph
from utils.pdf_reader import PDFReader
from utils.relations import generate_graph_data
from utils.document_store import DocumentStore
from schemas.contradiction import Contradiction
from utils.contradictions import classify_contradiction, postfilter_and_rank
import logging
import shutil
import tempfile
import os
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

pdf_reader = PDFReader()

document_store = DocumentStore()

@router.get("/list_documents", response_model=list[DatasetDocument])
def list_documents():
    if not document_store._initialized:
        document_store.initialize()
    return document_store.get_documents()


@router.get("/{document_id}/pdf")
def get_document_pdf(document_id: str):
    logger.info(f"Fetching PDF for document ID: {document_id}")

    pdf_path = document_store.get_path(document_id)

    if pdf_path and pdf_path.exists():
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=pdf_path.name
        )

    raise HTTPException(status_code=404, detail="Document not found")


@router.post("/process", response_model=Graph)
async def process_document(
    document_id: str = Form(...),
    file: UploadFile = File(None)
):
    tmp_path = None

    try:
        if file:
            if not file.filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail="Only PDF files are allowed")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name

        else:
            pdf_path = document_store.get_path(document_id)

            if not pdf_path:
                raise HTTPException(
                    status_code=404,
                    detail="Documento no encontrado localmente"
                )

            tmp_path = str(pdf_path)

        df_paragraphs, df_lines = pdf_reader.PDF_to_dataframe(tmp_path)

        logger.info("\n\n\n\n\n")

        logger.info(df_paragraphs)

        logger.info("\n\n\n\n\n")

        logger.info(df_lines)

        logger.info("\n\n\n\n\n")

        paragraphs = [
            Paragraph(
                id=f"{index}",
                documentId=document_id,
                page=int(row["page"]),
                paragraph_enum=int(row["paragraph_enum"]),
                text=row.get("clean_text", row["text"]),
                bbox=[
                    float(row["x0"]),
                    float(row["y0"]),
                    float(row["x1"]),
                    float(row["y1"]),
                ],
            )
            for index, row in df_paragraphs.iterrows()
        ]

        graph_data = generate_graph_data(paragraphs)

        id2text = {n["id"]: n["text"] for n in graph_data["nodes"]}
        
        raw_candidates = []
        for e in graph_data["edges"]:
            et = e.get("type", "")
            if not (et.startswith("reference") or et == "semantic_similarity"):
                continue

            a = id2text.get(e["source"], "")
            b = id2text.get(e["target"], "")
            if not a or not b:
                continue

            result = classify_contradiction(a, b, model="gpt-4o-mini")
            raw_candidates.append({
                "source": e["source"],
                "target": e["target"],
                "edge_type": et,
                "edge_score": e.get("score"),
                "result": result
            })

        ranked = postfilter_and_rank(raw_candidates)

        final_contradictions = []
        for c in ranked:
            source_node = next(n for n in paragraphs if n.id == c["source"])
            target_node = next(n for n in paragraphs if n.id == c["target"])
            
            ev_a = c["result"].get("evidence", {}).get("source", "")
            ev_b = c["result"].get("evidence", {}).get("target", "")

            bbox_a = pdf_reader.get_text_bbox(source_node.text, ev_a, df_lines, source_node.page)
            bbox_b = pdf_reader.get_text_bbox(target_node.text, ev_b, df_lines, target_node.page)

            final_contradictions.append(
                Contradiction(
                    source=c["source"],
                    target=c["target"],
                    type=c["result"].get("type", "other"),
                    confidence=float(c["result"].get("confidence", 0.0)),
                    edge_type=c["edge_type"],
                    edge_score=c.get("edge_score"),
                    evidence_a=ev_a,
                    evidence_b=ev_b,
                    evidence_a_bbox=bbox_a,
                    evidence_b_bbox=bbox_b,
                    evidence_a_page=source_node.page,
                    evidence_b_page=target_node.page,
                    summary=c["result"].get("summary", ""),
                    score=float(c.get("final_score", 0.0)),
                )
            )

        graph_data["contradictions"] = [c.model_dump() for c in final_contradictions]
        return Graph(**graph_data)  

    finally:
        if file and tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/upload", response_model=list[Paragraph])
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        df = pdf_reader.PDF_to_dataframe(tmp_path)
        doc_id = "upload_" + uuid.uuid4().hex[:8]

        paragraphs = [
            Paragraph(
                id=f"{doc_id}_{index}",
                documentId=doc_id,
                page=int(row["page"]),
                paragraph_enum=int(row["paragraph_enum"]),
                text=row.get("clean_text", row["text"]),
                bbox=[
                    float(row["x0"]),
                    float(row["y0"]),
                    float(row["x1"]),
                    float(row["y1"]),
                ],
            )
            for index, row in df.iterrows()
        ]

        return paragraphs

    except Exception as e:
        logger.error(f"Error processing uploaded document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.get("/")
def document_init():
    return {"message": "Document initialization endpoint"}
