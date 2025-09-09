import cloudinary.uploader
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile

def upload_to_cloudinary(file, folder=None, resource_type='auto'):
    """
    Upload a file to Cloudinary
    
    Args:
        file: File object (Django's InMemoryUploadedFile or TemporaryUploadedFile)
        folder: Optional folder in Cloudinary to store the file
        resource_type: Type of the file ('image', 'video', 'raw', 'auto')
        
    Returns:
        dict: Cloudinary upload response with file details
    """
    # Prepare upload options
    upload_options = {
        'resource_type': resource_type,
    }
    
    if folder:
        upload_options['folder'] = folder
    
    # Handle different file types
    if isinstance(file, (InMemoryUploadedFile, TemporaryUploadedFile)):
        # For files uploaded through Django forms
        response = cloudinary.uploader.upload(
            file,
            **upload_options
        )
    else:
        # For file paths or other file-like objects
        response = cloudinary.uploader.upload(
            file,
            **upload_options
        )
    
    return response

def delete_from_cloudinary(public_id, resource_type='image'):
    """
    Delete a file from Cloudinary
    
    Args:
        public_id: The public ID of the file to delete
        resource_type: Type of the resource ('image', 'video', 'raw')
        
    Returns:
        dict: Cloudinary delete response
    """
    return cloudinary.uploader.destroy(
        public_id,
        resource_type=resource_type,
        invalidate=True  # Invalidate CDN cache
    )
