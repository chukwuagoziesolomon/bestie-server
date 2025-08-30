import os
from pathlib import Path

def check_documents():
    # Check knowledge base directory
    kb_dir = Path('knowledge_base')
    print("\n=== Knowledge Base ===")
    if kb_dir.exists():
        print(f"Knowledge base directory: {kb_dir.absolute()}")
        files = list(kb_dir.glob('*'))
        if files:
            print("Documents found:")
            for f in files:
                print(f"- {f.name} ({f.stat().st_size} bytes)")
        else:
            print("No documents found in knowledge base")
    else:
        print("Knowledge base directory does not exist")
    
    # Check vector store
    vectorstore_dir = Path('vectorstore')
    print("\n=== Vector Store ===")
    if vectorstore_dir.exists():
        print(f"Vector store directory: {vectorstore_dir.absolute()}")
        files = list(vectorstore_dir.glob('*'))
        if files:
            print("Vector store files:")
            for f in files:
                print(f"- {f.name} ({f.stat().st_size} bytes)")
        else:
            print("No vector store files found")
    else:
        print("Vector store directory does not exist")

if __name__ == "__main__":
    check_documents()
