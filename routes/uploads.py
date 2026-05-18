from fastapi import APIRouter, UploadFile, File, HTTPException, Request
import cloudinary.uploader
import os

router = APIRouter()

@router.post("/image")
async def upload_image(request: Request, file: UploadFile = File(...)):
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type. Only JPEG, PNG, WEBP, and GIF are allowed.")

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
