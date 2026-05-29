import os
import uuid
import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from pydantic import BaseModel
from typing import List

from app.utils.db import get_db
from app.models import Document
from app.rag.vector_store import get_vector_store
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument

router = APIRouter()

class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    uploaded_at: datetime.datetime

    class Config:
        from_attributes = True
        from_attributes = True

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rag", "documents")

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Upload a document to be embedded and added to the vector database."""
    # Ensure the upload folder exists
    os.makedirs(DOCS_DIR, exist_ok=True)
    
    # Generate unique ID for the document
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    
    # Read the file content
    try:
        content_bytes = await file.read()
        content_text = content_bytes.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read text file: {str(e)}")

    # 1. Save the file to disk
    file_path = os.path.join(DOCS_DIR, file.filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content_text)

    # 2. Add document record to SQL Database
    db_doc = Document(
        id=doc_id,
        filename=file.filename,
        status="processing"
    )
    db.add(db_doc)
    await db.commit()

    # 3. Split content and upload to pgvector
    try:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_text(content_text)
        
        lc_docs = []
        for i, chunk in enumerate(chunks):
            lc_docs.append(
                LCDocument(
                    page_content=chunk,
                    metadata={
                        "document_id": doc_id,
                        "filename": file.filename,
                        "chunk_index": i
                    }
                )
            )
            
        vector_store = get_vector_store()
        # Add chunks asynchronously (LangChain's add_documents uses sync execution under the hood)
        vector_store.add_documents(lc_docs)
        
        # Update status in DB
        db_doc.status = "embedded"
        await db.commit()
        await db.refresh(db_doc)
        
    except Exception as e:
        # Update status to error
        db_doc.status = f"error: {str(e)}"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

    return db_doc

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all documents currently stored in the agent's knowledge base."""
    result = await db.execute(select(Document))
    docs = result.scalars().all()
    return docs

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Remove a document and its vector embeddings from the knowledge base."""
    # Find the document in relational table
    result = await db.execute(select(Document).where(Document.id == doc_id))
    db_doc = result.scalar_one_or_none()
    
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 1. Delete matching vector embeddings from pgvector database table
    try:
        # LangChain PGVector uses 'langchain_pg_embedding' table
        await db.execute(
            text("DELETE FROM langchain_pg_embedding WHERE cmetadata->>'document_id' = :doc_id"),
            {"doc_id": doc_id}
        )
    except Exception as e:
        print(f"Warning: Failed to clean up embeddings from langchain_pg_embedding: {e}")

    # 2. Delete the physical file from disk
    file_path = os.path.join(DOCS_DIR, db_doc.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Warning: Failed to remove file from disk: {e}")

    # 3. Delete from relational database
    await db.delete(db_doc)
    await db.commit()
    
    return {"message": f"Document {doc_id} and its vector embeddings removed from memory."}

@router.get("/documents/{doc_id}/chunks")
async def get_document_chunks(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve all text chunks/embeddings stored for a specific document in pgvector."""
    try:
        result = await db.execute(
            text("SELECT document, cmetadata FROM langchain_pg_embedding WHERE cmetadata->>'document_id' = :doc_id"),
            {"doc_id": doc_id}
        )
        rows = result.all()
        chunks = []
        for r in rows:
            chunks.append({
                "content": r[0],
                "metadata": r[1]
            })
        return {"chunks": chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_knowledge_base(query: str = Query(..., description="Query string for semantic search")):
    """Perform a vector-based similarity search in the PGVector store."""
    try:
        vector_store = get_vector_store()
        docs = vector_store.similarity_search(query, k=5)
        results = []
        for doc in docs:
            results.append({
                "page_content": doc.page_content,
                "metadata": doc.metadata
            })
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

