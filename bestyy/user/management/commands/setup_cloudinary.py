"""
Django management command to set up Cloudinary upload preset.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import cloudinary
import cloudinary.api


class Command(BaseCommand):
    help = 'Set up Cloudinary upload preset for the application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--preset-name',
            type=str,
            default='bestyy_upload_preset',
            help='Name of the upload preset to create'
        )
        parser.add_argument(
            '--unsigned',
            action='store_true',
            help='Create an unsigned (public) upload preset'
        )

    def handle(self, *args, **options):
        preset_name = options['preset_name']
        unsigned = options['unsigned']
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY['cloud_name'],
            api_key=settings.CLOUDINARY['api_key'],
            api_secret=settings.CLOUDINARY['api_secret']
        )
        
        try:
            # Check if preset already exists
            try:
                existing_preset = cloudinary.api.upload_preset(preset_name)
                self.stdout.write(
                    self.style.WARNING(f'Upload preset "{preset_name}" already exists')
                )
                self.stdout.write(f'Existing preset details: {existing_preset}')
                return
            except cloudinary.api.NotFound:
                pass  # Preset doesn't exist, we can create it
            
            # Create the upload preset
            preset_options = {
                'name': preset_name,
                'unsigned': unsigned,
                'folder': 'bestyy_uploads',
                'resource_type': 'image',
                'transformation': [
                    {'width': 1200, 'height': 800, 'crop': 'limit', 'quality': 'auto'},
                    {'fetch_format': 'auto'}
                ],
                'eager': [
                    {'width': 800, 'height': 600, 'crop': 'fill', 'quality': 'auto'},
                    {'width': 400, 'height': 300, 'crop': 'fill', 'quality': 'auto'},
                    {'width': 200, 'height': 150, 'crop': 'fill', 'quality': 'auto'}
                ],
                'eager_async': True,
                'eager_notification_url': None,
                'tags': ['bestyy', 'auto_upload'],
                'allowed_formats': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
                'max_file_size': 10485760,  # 10MB
                'max_image_width': 4000,
                'max_image_height': 4000,
            }
            
            if unsigned:
                preset_options['unsigned'] = True
                self.stdout.write('Creating unsigned (public) upload preset...')
            else:
                self.stdout.write('Creating signed upload preset...')
            
            result = cloudinary.api.create_upload_preset(**preset_options)
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created upload preset: {preset_name}')
            )
            self.stdout.write(f'Preset details: {result}')
            
            # Update settings if needed
            if not settings.CLOUDINARY.get('upload_preset'):
                self.stdout.write(
                    self.style.WARNING(
                        'Remember to add CLOUDINARY_UPLOAD_PRESET to your environment variables'
                    )
                )
                self.stdout.write(f'Set CLOUDINARY_UPLOAD_PRESET={preset_name}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating upload preset: {str(e)}')
            )
            raise
