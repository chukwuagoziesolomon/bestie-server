import cloudinary
import cloudinary.uploader
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.conf import settings

def upload_to_cloudinary(file, folder=None, resource_type='auto', upload_preset=None):
    """
    Upload a file to Cloudinary
    
    Args:
        file: File object (Django's InMemoryUploadedFile or TemporaryUploadedFile)
        folder: Optional folder in Cloudinary to store the file
        resource_type: Type of the file ('image', 'video', 'raw', 'auto')
        upload_preset: Optional upload preset name
        
    Returns:
        dict: Cloudinary upload response with file details
    """
    # Configure Cloudinary with settings
    cloudinary.config(
        cloud_name=settings.CLOUDINARY['cloud_name'],
        api_key=settings.CLOUDINARY['api_key'],
        api_secret=settings.CLOUDINARY['api_secret']
    )
    
    # Prepare upload options
    upload_options = {
        'resource_type': resource_type,
    }
    
    if folder:
        upload_options['folder'] = folder
    
    # Use upload preset if provided or from settings
    if upload_preset:
        upload_options['upload_preset'] = upload_preset
    elif settings.CLOUDINARY.get('upload_preset'):
        upload_options['upload_preset'] = settings.CLOUDINARY['upload_preset']
    
    # If no upload preset is configured, use signed upload
    if not upload_options.get('upload_preset'):
        # For signed uploads, we need the API secret
        if not settings.CLOUDINARY.get('api_secret'):
            raise Exception("Cloudinary API secret is required for signed uploads")
    
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
