import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_STORE_PATH = "vectorstore"

def load_documents(docs_dir: str = "knowledge_base"):
    """Load documents from the knowledge base directory."""
    documents = []
    docs_path = Path(docs_dir)
    
    if not docs_path.exists():
        os.makedirs(docs_path, exist_ok=True)
        print(f"Created {docs_dir} directory. Please add your documents here.")
        return []
    
    for file_path in docs_path.glob("*"):
        try:
            if file_path.suffix.lower() == ".pdf":
                loader = PyPDFLoader(str(file_path))
            elif file_path.suffix.lower() in [".txt", ".md"]:
                loader = TextLoader(str(file_path))
            else:
                print(f"Unsupported file format: {file_path}")
                continue
                
            documents.extend(loader.load())
            print(f"Loaded {file_path}")
            
        except Exception as e:
            print(f"Error loading {file_path}: {str(e)}")
    
    return documents

def chunk_documents(documents):
    """Split documents into chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    return text_splitter.split_documents(documents)

def create_vector_store(chunks):
    """Create and save FAISS vector store."""
    # Initialize embeddings model
    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
    
    # Create and save vector store
    vectorstore = FAISS.from_documents(chunks, embeddings)
    os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
    vectorstore.save_local(VECTOR_STORE_PATH)
    return vectorstore

def main():
    print("Starting document ingestion...")
    
    # Load documents
    documents = load_documents()
    if not documents:
        print("No documents found. Please add documents to the 'knowledge_base' directory.")
        return
    
    # Chunk documents
    print("Chunking documents...")
    chunks = chunk_documents(documents)
    print(f"Split into {len(chunks)} chunks of text.")
    
    # Create and save vector store
    print("Creating vector store...")
    vectorstore = create_vector_store(chunks)
    print(f"Vector store created successfully at: {VECTOR_STORE_PATH}")
    print(f"Total vectors: {vectorstore.index.ntotal}")

if __name__ == "__main__":
    main()
