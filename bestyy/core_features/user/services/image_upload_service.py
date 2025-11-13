import hashlib
import os
from typing import Optional, Dict, Any, Tuple
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.conf import settings
from utils.cloudinary_utils import upload_to_cloudinary, delete_from_cloudinary
from .models import ImageUpload


class ImageUploadService:
    """
    Service for handling image uploads with duplicate detection and Cloudinary integration.
    """

    # Image type configurations
    IMAGE_TYPES = {
        'vendor_logo': {
            'folder': 'vendor_logos',
            'max_size': 5 * 1024 * 1024,  # 5MB
            'allowed_formats': ['jpg', 'jpeg', 'png', 'webp'],
            'transformations': {'width': 300, 'height': 300, 'crop': 'fill'}
        },
        'vendor_cover': {
            'folder': 'vendor_cover_photos',
            'max_size': 10 * 1024 * 1024,  # 10MB
            'allowed_formats': ['jpg', 'jpeg', 'png', 'webp'],
            'transformations': {'width': 1200, 'height': 400, 'crop': 'fill'}
        },
        'menu_item': {
            'folder': 'menu_items',
            'max_size': 5 * 1024 * 1024,  # 5MB
            'allowed_formats': ['jpg', 'jpeg', 'png', 'webp'],
            'transformations': {'width': 800, 'height': 600, 'crop': 'fill'}
        },
        'courier_photo': {
            'folder': 'courier_photos',
            'max_size': 5 * 1024 * 1024,  # 5MB
            'allowed_formats': ['jpg', 'jpeg', 'png', 'webp'],
            'transformations': {'width': 300, 'height': 300, 'crop': 'fill'}
        }
    }

    @staticmethod
    def calculate_image_hash(file) -> str:
        """
        Calculate SHA256 hash of image file for duplicate detection.

        Args:
            file: Django uploaded file object

        Returns:
            str: SHA256 hash of the file
        """
        hasher = hashlib.sha256()

        if isinstance(file, (InMemoryUploadedFile, TemporaryUploadedFile)):
            # For uploaded files, read from file pointer
            file.seek(0)
            for chunk in iter(lambda: file.read(4096), b""):
                hasher.update(chunk)
            file.seek(0)  # Reset file pointer
        else:
            # For file paths or other file-like objects
            with open(file, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)

        return hasher.hexdigest()

    @staticmethod
    def validate_image(file, image_type: str) -> Tuple[bool, str]:
        """
        Validate image file based on type requirements.

        Args:
            file: Django uploaded file object
            image_type: Type of image (vendor_logo, menu_item, etc.)

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if image_type not in ImageUploadService.IMAGE_TYPES:
            return False, f"Invalid image type: {image_type}"

        config = ImageUploadService.IMAGE_TYPES[image_type]

        # Check file size
        if file.size > config['max_size']:
            max_size_mb = config['max_size'] / (1024 * 1024)
            return False, f"File size exceeds {max_size_mb}MB limit"

        # Check file extension
        file_ext = os.path.splitext(file.name)[1].lower().lstrip('.')
        if file_ext not in config['allowed_formats']:
            allowed = ', '.join(config['allowed_formats'])
            return False, f"File format not allowed. Allowed formats: {allowed}"

        return True, ""

    @staticmethod
    def check_duplicate(image_hash: str, image_type: str, exclude_id: Optional[int] = None) -> Optional[ImageUpload]:
        """
        Check if an image with the same hash already exists.

        Args:
            image_hash: SHA256 hash of the image
            image_type: Type of image
            exclude_id: ID to exclude from search (for updates)

        Returns:
            ImageUpload object if duplicate found, None otherwise
        """
        queryset = ImageUpload.objects.filter(
            image_hash=image_hash,
            image_type=image_type,
            is_active=True
        )

        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        return queryset.first()

    @staticmethod
    def upload_image(file, image_type: str, user_id: int, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Upload image with duplicate detection and Cloudinary integration.

        Args:
            file: Django uploaded file object
            image_type: Type of image (vendor_logo, menu_item, etc.)
            user_id: ID of the user uploading the image
            metadata: Additional metadata for the image

        Returns:
            Dict containing upload result with keys:
            - success: bool
            - image_upload: ImageUpload object (if successful)
            - duplicate: bool (if duplicate found)
            - existing_image: ImageUpload object (if duplicate)
            - error: error message (if failed)
        """
        try:
            # Validate image
            is_valid, error_msg = ImageUploadService.validate_image(file, image_type)
            if not is_valid:
                return {
                    'success': False,
                    'error': error_msg
                }

            # Calculate hash for duplicate detection
            image_hash = ImageUploadService.calculate_image_hash(file)

            # Check for duplicates
            existing_image = ImageUploadService.check_duplicate(image_hash, image_type)
            if existing_image:
                return {
                    'success': True,
                    'duplicate': True,
                    'existing_image': existing_image,
                    'image_upload': existing_image  # Return existing for compatibility
                }

            # Upload to Cloudinary
            config = ImageUploadService.IMAGE_TYPES[image_type]
            upload_result = upload_to_cloudinary(
                file=file,
                folder=config['folder'],
                resource_type='image'
            )

            if not upload_result or 'error' in upload_result:
                return {
                    'success': False,
                    'error': upload_result.get('error', {}).get('message', 'Upload failed')
                }

            # Create ImageUpload record
            image_upload = ImageUpload.objects.create(
                user_id=user_id,
                image_type=image_type,
                image_hash=image_hash,
                cloudinary_public_id=upload_result['public_id'],
                cloudinary_url=upload_result['secure_url'],
                original_filename=file.name,
                file_size=file.size,
                metadata=metadata or {},
                is_active=True
            )

            return {
                'success': True,
                'duplicate': False,
                'image_upload': image_upload
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"Upload failed: {str(e)}"
            }

    @staticmethod
    def delete_image(image_upload: ImageUpload) -> bool:
        """
        Delete image from Cloudinary and mark as inactive.

        Args:
            image_upload: ImageUpload object to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete from Cloudinary
            delete_result = delete_from_cloudinary(
                public_id=image_upload.cloudinary_public_id,
                resource_type='image'
            )

            # Mark as inactive (soft delete)
            image_upload.is_active = False
            image_upload.save()

            return True

        except Exception as e:
            # Log error but don't fail - image might already be deleted
            print(f"Error deleting image {image_upload.id}: {str(e)}")
            return False

    @staticmethod
    def get_image_url(image_upload: ImageUpload, transformations: Optional[Dict[str, Any]] = None) -> str:
        """
        Get optimized image URL with optional transformations.

        Args:
            image_upload: ImageUpload object
            transformations: Cloudinary transformation parameters

        Returns:
            str: Optimized image URL
        """
        if not transformations:
            return image_upload.cloudinary_url

        # Apply transformations using Cloudinary URL API
        # This is a simplified version - in production, use Cloudinary's Python SDK
        base_url = image_upload.cloudinary_url
        # For now, return the base URL - implement transformation logic as needed
        return base_url

    @staticmethod
    def cleanup_unused_images():
        """
        Clean up images that are no longer referenced by any model.
        This should be run as a periodic task.
        """
        # Find images not referenced by any model
        # This is a simplified implementation - extend based on your models
        unused_images = ImageUpload.objects.filter(
            is_active=True
        ).exclude(
            # Add Q objects for each model that references images
            # Example: Q(vendor_logos__isnull=False) | Q(menu_items__isnull=False)
        )

        deleted_count = 0
        for image in unused_images:
            if ImageUploadService.delete_image(image):
                deleted_count += 1

        return deleted_count