# Local RAG Setup for Customer Service Chatbot

This setup uses LangChain and FAISS to create a local RAG (Retrieval-Augmented Generation) system for your customer service chatbot.

## Setup

1. Install the required dependencies:
   ```bash
   pip install -r requirements-rag.txt
   ```

2. Create a `knowledge_base` directory and add your documents (PDF/TXT) there.

3. Run the ingestion script:
   ```bash
   python api/ingest.py
   ```
   This will:
   - Load documents from the `knowledge_base` directory
   - Split them into chunks
   - Create embeddings using the `all-MiniLM-L6-v2` model
   - Save the vector store to the `vectorstore` directory

## Document Formats Supported
- PDF (.pdf)
- Text (.txt)
- Markdown (.md)

## Next Steps
1. Add your documents to the `knowledge_base` directory
2. Run the ingestion script to process them
3. The vector store will be saved in the `vectorstore` directory
