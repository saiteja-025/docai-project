import cloudinary
import cloudinary.uploader
import os
from backend.core.config import settings


def setup_cloudinary():
    """Configure the Cloudinary SDK using CLOUDINARY_URL or individual credentials."""
    url = settings.CLOUDINARY_URL or os.environ.get("CLOUDINARY_URL", "")
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    api_key = os.environ.get("CLOUDINARY_API_KEY")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")

    if url:
        os.environ["CLOUDINARY_URL"] = url
        try:
            cloudinary.config()._load_from_url(url)
        except Exception:
            cloudinary.reset_config()
    elif cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )


def upload_pdf_to_cloudinary(file_bytes: bytes, filename: str) -> str:
    """Upload a document to Cloudinary and return the secure URL.

    Falls back to a mock URL if Cloudinary is not configured or the upload
    fails, so that document processing (text extraction, FAISS indexing,
    summarisation) always completes successfully regardless of storage status.
    """
    url = settings.CLOUDINARY_URL or os.environ.get("CLOUDINARY_URL", "")
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    api_key = os.environ.get("CLOUDINARY_API_KEY")

    if not url and not (cloud_name and api_key):
        print("[Cloudinary] Credentials not set — using local placeholder URL.")
        return f"mock_url_for_{filename}"

    setup_cloudinary()

    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            resource_type="raw",
            use_filename=True,
            unique_filename=True,
            folder="docai_uploads",
        )
        secure_url = result.get("secure_url", "")
        print(f"[Cloudinary] Upload OK: {secure_url}")
        return secure_url
    except Exception as e:
        # Log the error but do NOT raise — the document text is persisted in
        # PostgreSQL so the RAG pipeline works even without the Cloudinary URL.
        print(f"[Cloudinary] Upload failed (non-fatal): {e}")
        return f"mock_url_for_{filename}"
