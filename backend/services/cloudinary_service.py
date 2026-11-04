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

    Raises an exception if Cloudinary is not configured or if the upload fails,
    ensuring that only files genuinely stored in Cloudinary are marked as ready.
    """
    url = settings.CLOUDINARY_URL or os.environ.get("CLOUDINARY_URL", "")
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    api_key = os.environ.get("CLOUDINARY_API_KEY")

    if not url and not (cloud_name and api_key):
        raise ValueError(
            "Cloudinary credentials are NOT configured. "
            "Please provide CLOUDINARY_URL or CLOUDINARY_CLOUD_NAME/KEY/SECRET."
        )

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
        if not secure_url:
            raise RuntimeError("Cloudinary upload succeeded but returned an empty secure_url.")
        print(f"[Cloudinary] Upload OK: {secure_url}")
        return secure_url
    except Exception as e:
        print(f"[Cloudinary] Upload failed: {e}")
        raise RuntimeError(f"Cloudinary upload failed: {e}") from e


def delete_from_cloudinary(public_id_or_url: str):
    """Delete a raw document file from Cloudinary."""
    if not public_id_or_url or "mock_url" in public_id_or_url:
        return

    setup_cloudinary()
    try:
        # Extract public_id if full URL was passed
        public_id = public_id_or_url
        if "res.cloudinary.com" in public_id_or_url:
            # e.g., .../raw/upload/v12345/docai_uploads/filename.pdf
            parts = public_id_or_url.split("/upload/")[-1].split("/")
            # skip version if present (e.g. v12345)
            if parts[0].startswith("v") and parts[0][1:].isdigit():
                parts = parts[1:]
            public_id = "/".join(parts)

        result = cloudinary.uploader.destroy(public_id, resource_type="raw")
        print(f"[Cloudinary] Delete result for {public_id}: {result}")
        return result
    except Exception as e:
        print(f"[Cloudinary] Delete failed (non-fatal): {e}")
        return None
