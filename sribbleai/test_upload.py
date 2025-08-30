import os
from pathlib import Path
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scribbleintimeai.settings')
import django
django.setup()

from scribble.views import upload_document
from scribble.models import KnowledgeDocument

def test_upload():
    # Create a test PDF file
    test_pdf = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<< /Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<< /Type /Page\n/Parent 2 0 R\n/Resources << /Font << /F1 4 0 R >> >>
/Contents 5 0 R
>>\nendobj\n4 0 obj\n<< /Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Test Document) Tj\nET\nendstream\nendobj\n\n%%EOF'

    # Create a test request
    factory = RequestFactory()
    request = factory.post('/api/documents/upload/', {
        'file': SimpleUploadedFile('test.pdf', test_pdf, content_type='application/pdf')
    })

    # Call the upload view
    response = upload_document(request)
    print("Upload response:", response.content)

    # Check if document was saved
    docs = KnowledgeDocument.objects.all()
    print(f"Documents in database: {docs.count()}")
    for doc in docs:
        print(f"- {doc.title} (ID: {doc.id})")
        print(f"  Path: {doc.file.path if doc.file else 'No file'}")
        print(f"  Exists: {os.path.exists(doc.file.path) if doc.file else False}")

    # Check knowledge base directory
    kb_dir = Path('knowledge_base')
    print(f"Knowledge base exists: {kb_dir.exists()}")
    if kb_dir.exists():
        print("Files in knowledge base:")
        for f in kb_dir.glob('*'):
            print(f"- {f.name} ({f.stat().st_size} bytes)")

    # Check vector store
    vectorstore_dir = Path('vectorstore')
    print(f"Vector store exists: {vectorstore_dir.exists()}")
    if vectorstore_dir.exists():
        print("Files in vector store:")
        for f in vectorstore_dir.glob('*'):
            print(f"- {f.name} ({f.stat().st_size} bytes)")

if __name__ == "__main__":
    test_upload()
