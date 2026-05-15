from fastapi import APIRouter, UploadFile, File, HTTPException, Request
import shutil
import os
import uuid
from datetime import datetime

router = APIRouter()

UPLOAD_DIR = os.path.abspath(os.path.join("uploads", "images"))

# Ensure upload directory exists
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/image")
async def upload_image(request: Request, file: UploadFile = File(...)):
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid image type. Only JPEG, PNG, WEBP, and GIF are allowed.")

    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4().hex}_{int(datetime.now().timestamp())}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")

    # Return the absolute URL
    return {"url": f"http://localhost:8000/uploads/images/{unique_filename}"}
