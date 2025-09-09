"""
Utility functions for handling Cloudinary image uploads and transformations for menu items.
"""
import cloudinary
import cloudinary.uploader
from django.conf import settings


def upload_menu_image(file, vendor_id, folder='menu_items'):
    """
    Upload a menu item image to Cloudinary with proper folder structure.
    
    Args:
        file: The uploaded file
        vendor_id: ID of the vendor (for folder organization)
        folder: Base folder name (default: 'menu_items')
    
    Returns:
        dict: Cloudinary upload response
    """
    try:
        # Create folder path: menu_items/vendor_{vendor_id}/
        upload_folder = f"{folder}/vendor_{vendor_id}"
        
        # Upload to Cloudinary with transformations
        response = cloudinary.uploader.upload(
            file,
            folder=upload_folder,
            resource_type="image",
            transformation=[
                {"width": 800, "height": 600, "crop": "fill", "quality": "auto"},
                {"fetch_format": "auto"}
            ],
            eager=[
                {"width": 400, "height": 300, "crop": "fill", "quality": "auto"},
                {"width": 200, "height": 150, "crop": "fill", "quality": "auto"}
            ]
        )
        
        return response
    except Exception as e:
        raise Exception(f"Failed to upload image to Cloudinary: {str(e)}")


def get_menu_image_url(public_id, transformation=None):
    """
    Get Cloudinary URL for a menu item image with optional transformations.
    
    Args:
        public_id: Cloudinary public ID
        transformation: Optional transformation parameters
    
    Returns:
        str: Cloudinary URL
    """
    try:
        if transformation:
            return cloudinary.CloudinaryImage(public_id).build_url(transformation=transformation)
        else:
            return cloudinary.CloudinaryImage(public_id).build_url()
    except Exception as e:
        raise Exception(f"Failed to generate Cloudinary URL: {str(e)}")


def delete_menu_image(public_id):
    """
    Delete a menu item image from Cloudinary.
    
    Args:
        public_id: Cloudinary public ID
    
    Returns:
        dict: Cloudinary delete response
    """
    try:
        response = cloudinary.uploader.destroy(public_id, resource_type="image")
        return response
    except Exception as e:
        raise Exception(f"Failed to delete image from Cloudinary: {str(e)}")


def get_menu_image_transformations():
    """
    Get predefined image transformations for menu items.
    
    Returns:
        dict: Available transformations
    """
    return {
        'thumbnail': {'width': 200, 'height': 150, 'crop': 'fill', 'quality': 'auto'},
        'medium': {'width': 400, 'height': 300, 'crop': 'fill', 'quality': 'auto'},
        'large': {'width': 800, 'height': 600, 'crop': 'fill', 'quality': 'auto'},
        'original': {}  # No transformation
    }


def generate_menu_image_urls(public_id):
    """
    Generate multiple image URLs for different sizes.
    
    Args:
        public_id: Cloudinary public ID
    
    Returns:
        dict: URLs for different image sizes
    """
    transformations = get_menu_image_transformations()
    urls = {}
    
    for size, transformation in transformations.items():
        try:
            urls[size] = get_menu_image_url(public_id, transformation)
        except Exception as e:
            urls[size] = None
    
    return urls


