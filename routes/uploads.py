from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends
import cloudinary.uploader
import os
from utils.auth import require_admin

router = APIRouter()

@router.post("/image")
async def upload_image(request: Request, file: UploadFile = File(...), admin: dict = Depends(require_admin)):
    # Basic validation to ensure it's an image
    if not file.content_type.startswith("image/") and file.content_type != "application/octet-stream":
        raise HTTPException(status_code=400, detail=f"Invalid file type ({file.content_type}). Please upload an image.")

    try:
        # Upload the file directly to Cloudinary without saving it locally
        result = cloudinary.uploader.upload(
            file.file,
            folder="aaj_tech/images",
            resource_type="image"
        )
        # Return the secure URL provided by Cloudinary
        return {"url": result.get("secure_url")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image to Cloudinary: {str(e)}")
