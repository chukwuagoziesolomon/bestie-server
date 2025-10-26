"""
Utility functions for handling Cloudinary image uploads and transformations for verification documents.
"""
import cloudinary
import cloudinary.uploader
from django.conf import settings


def get_verification_document_url(file_field):
    """
    Get the proper URL for a verification document (profile photo, ID, etc.).
    Handles both Cloudinary and local storage.
    
    Args:
        file_field: Django ImageField or FileField
    
    Returns:
        str: Full URL to the document
    """
    if not file_field:
        return None
    
    try:
        # If using Cloudinary, the URL is already absolute
        if hasattr(settings, 'DEFAULT_FILE_STORAGE') and 'cloudinary' in settings.DEFAULT_FILE_STORAGE:
            return file_field.url
        else:
            # For local storage, we need to build the absolute URI
            from django.contrib.sites.models import Site
            from django.conf import settings
            
            if hasattr(settings, 'BASE_URL'):
                base_url = settings.BASE_URL
            else:
                base_url = f"http://{Site.objects.get_current().domain}"
            
            return f"{base_url}{file_field.url}"
    except Exception as e:
        # Fallback to just the URL
        return file_field.url if file_field else None


def get_verification_document_urls(profile):
    """
    Get all verification document URLs for a vendor or courier profile.
    
    Args:
        profile: VendorProfile or CourierProfile instance
    
    Returns:
        dict: Dictionary of document URLs
    """
    urls = {}
    
    if hasattr(profile, 'business_name'):  # Vendor profile
        urls['logo'] = get_verification_document_url(getattr(profile, 'logo', None))
        urls['cac_document'] = get_verification_document_url(getattr(profile, 'cac_document', None))
        urls['valid_id'] = get_verification_document_url(getattr(profile, 'valid_id', None))
    else:  # Courier profile
        urls['profile_photo'] = get_verification_document_url(getattr(profile, 'profile_photo', None))
        urls['id_upload'] = get_verification_document_url(getattr(profile, 'id_upload', None))
    
    return urls


def upload_verification_document(file, user_id, document_type, folder='verification_documents'):
    """
    Upload a verification document to Cloudinary with proper folder structure.
    
    Args:
        file: The uploaded file
        user_id: ID of the user (for folder organization)
        document_type: Type of document (logo, id_upload, etc.)
        folder: Base folder name (default: 'verification_documents')
    
    Returns:
        dict: Cloudinary upload response
    """
    try:
        # Create folder path: verification_documents/user_{user_id}/document_type/
        upload_folder = f"{folder}/user_{user_id}/{document_type}"
        
        # Upload to Cloudinary with appropriate transformations
        response = cloudinary.uploader.upload(
            file,
            folder=upload_folder,
            resource_type="image",
            transformation=[
                {"width": 1200, "height": 800, "crop": "limit", "quality": "auto"},
                {"fetch_format": "auto"}
            ]
        )
        
        return response
    except Exception as e:
        raise Exception(f"Failed to upload verification document to Cloudinary: {str(e)}")


def delete_verification_document(public_id):
    """
    Delete a verification document from Cloudinary.
    
    Args:
        public_id: Cloudinary public ID
    
    Returns:
        dict: Cloudinary delete response
    """
    try:
        response = cloudinary.uploader.destroy(public_id, resource_type="image")
        return response
    except Exception as e:
        raise Exception(f"Failed to delete verification document from Cloudinary: {str(e)}")


def get_verification_document_transformations():
    """
    Get predefined image transformations for verification documents.
    
    Returns:
        dict: Available transformations
    """
    return {
        'thumbnail': {'width': 200, 'height': 150, 'crop': 'fill', 'quality': 'auto'},
        'medium': {'width': 600, 'height': 400, 'crop': 'limit', 'quality': 'auto'},
        'large': {'width': 1200, 'height': 800, 'crop': 'limit', 'quality': 'auto'},
        'original': {}  # No transformation
    }
