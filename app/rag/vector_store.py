import os
from langchain_community.vectorstores import PGVector
from app.rag.embeddings import get_embeddings
from app.rag.document_loader import load_and_split_documents

# Retrieve the database URL, replacing asyncpg with psycopg2 driver if necessary for LangChain
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_db"
)
CONNECTION_STRING = DATABASE_URL
if "asyncpg" in CONNECTION_STRING:
    CONNECTION_STRING = CONNECTION_STRING.replace("asyncpg", "psycopg2")

def get_vector_store():
    """Returns the initialized PGVector store for querying."""
    return PGVector(
        connection_string=CONNECTION_STRING,
        embedding_function=get_embeddings(),
        collection_name="project_knowledge"
    )

def ingest_documents():
    """Utility function to load docs, convert them to vectors, and save them in PGVector."""
    print("Loading and splitting documents from /documents folder...")
    splits = load_and_split_documents()
    
    if not splits:
        print("No documents found in /documents to ingest.")
        return
        
    print(f"Found {len(splits)} chunks. Ingesting into PGVector...")
    
    vector_store = PGVector.from_documents(
        documents=splits,
        embedding=get_embeddings(),
        collection_name="project_knowledge",
        connection_string=CONNECTION_STRING
    )
    
    print("Ingestion complete. PGVector database is ready for RAG.")
    return vector_store

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    ingest_documents()
