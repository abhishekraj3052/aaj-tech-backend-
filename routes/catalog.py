from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from typing import List
from pydantic import BaseModel

router = APIRouter()

UPLOAD_DIR = "uploads/catalogs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class CatalogInfo(BaseModel):
    name: str
    filename: str
    url: str

@router.post("/upload")
async def upload_catalog(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"filename": file.filename, "status": "success"}

@router.get("/")
async def list_catalogs():
    files = os.listdir(UPLOAD_DIR)
    return [{"name": f, "url": f"/api/catalog/download/{f}"} for f in files if f.endswith(".pdf")]

@router.get("/download/{filename}")
async def get_catalog(filename: str):
    from fastapi.responses import FileResponse
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
