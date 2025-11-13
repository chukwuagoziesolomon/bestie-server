from django.core.management.base import BaseCommand
from urllib.parse import unquote
import re

from bestyy.core_features.user.models import MenuItem, VendorProfile

CLOUDINARY_UPLOAD_REGEX = re.compile(r"/upload/(?:v\d+/)?(.+)")


def extract_public_id(value: str) -> str | None:
    if not value or not isinstance(value, str):
        return None
    match = CLOUDINARY_UPLOAD_REGEX.search(value)
    if match:
        return unquote(match.group(1))
    return None


class Command(BaseCommand):
    help = "Normalize Cloudinary images: convert stored full URLs to public_ids for ImageFields."

    def handle(self, *args, **options):
        updated_menu = 0
        updated_vendor = 0

        # Fix MenuItem.image
        for item in MenuItem.objects.all().only('id', 'image'):
            img_name = getattr(item.image, 'name', None) or None
            if isinstance(img_name, str) and img_name.startswith('http'):
                public_id = extract_public_id(img_name)
                if public_id:
                    item.image = public_id
                    item.save(update_fields=['image'])
                    updated_menu += 1

        # Fix VendorProfile image fields
        vendor_qs = VendorProfile.objects.all()
        for vendor in vendor_qs:
            changed = False
            for field_name in ['logo', 'cover_image', 'cover_photo']:
                if hasattr(vendor, field_name):
                    field = getattr(vendor, field_name)
                    img_name = getattr(field, 'name', None) or None
                    if isinstance(img_name, str) and img_name.startswith('http'):
                        public_id = extract_public_id(img_name)
                        if public_id:
                            setattr(vendor, field_name, public_id)
                            changed = True
            if changed:
                vendor.save()
                updated_vendor += 1

        self.stdout.write(self.style.SUCCESS(
            f"Updated MenuItem images: {updated_menu}; Updated VendorProfile images: {updated_vendor}"
        ))


















