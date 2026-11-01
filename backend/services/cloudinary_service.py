import cloudinary
import cloudinary.uploader
import os
from backend.core.config import settings


def setup_cloudinary():
    """Configure the Cloudinary SDK using the CLOUDINARY_URL from settings."""
    url = settings.CLOUDINARY_URL or os.environ.get("CLOUDINARY_URL", "")
    if url:
        # Explicitly pass the URL — more reliable than relying on auto-detection
        cloudinary.config(cloudinary_url=url)


def upload_pdf_to_cloudinary(file_bytes: bytes, filename: str) -> str:
    """Upload a document to Cloudinary and return the secure URL.

    Falls back to a mock URL if Cloudinary is not configured or the upload
    fails, so that document processing (text extraction, FAISS indexing,
    summarisation) always completes successfully regardless of storage status.
    """
    url = settings.CLOUDINARY_URL or os.environ.get("CLOUDINARY_URL", "")

    if not url:
        print("[Cloudinary] CLOUDINARY_URL not set — using mock URL.")
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
        return f"cloudinary_failed_url_for_{filename}"
