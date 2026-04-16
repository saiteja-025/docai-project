import cloudinary
import cloudinary.uploader
from backend.core.config import settings

def setup_cloudinary():
    if settings.CLOUDINARY_URL:
        # cloudinary package will automatically read the CLOUDINARY_URL format
        cloudinary.config()

def upload_pdf_to_cloudinary(file_bytes: bytes, filename: str) -> str:
    """Uploads a PDF to Cloudinary and returns the secure URL."""
    setup_cloudinary()
    
    if not settings.CLOUDINARY_URL:
        # Fallback for local development if no Cloudinary URL
        return f"mock_url_for_{filename}"
        
    try:
        result = cloudinary.uploader.upload(
            file_bytes, 
            resource_type="raw", 
            use_filename=True,
            unique_filename=True,
            public_id=filename.split('.')[0]
        )
        return result.get('secure_url')
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        raise e
