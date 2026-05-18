from fastapi import APIRouter, UploadFile, File, HTTPException
import cloudinary.uploader
import cloudinary.api
import os

router = APIRouter()

@router.post("/upload")
async def upload_catalog(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Upload the PDF directly to Cloudinary as a raw file
        result = cloudinary.uploader.upload(
            file.file,
            folder="aaj_tech/catalogs",
            resource_type="raw",
            public_id=file.filename
        )
        return {"filename": file.filename, "status": "success", "url": result.get("secure_url")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save catalog to Cloudinary: {str(e)}")

@router.get("/")
async def list_catalogs():
    try:
        # Query Cloudinary for files in the aaj_tech/catalogs folder
        resources = cloudinary.api.resources(
            type="upload", 
            prefix="aaj_tech/catalogs/", 
            resource_type="raw"
        )
        
        catalogs = []
        for res in resources.get('resources', []):
            # Extract filename from public_id
            filename = res['public_id'].split('/')[-1]
            if filename.endswith('.pdf'):
                catalogs.append({
                    "name": filename,
                    "url": res['secure_url']
                })
        return catalogs
    except Exception as e:
        # If folder doesn't exist yet or other error, return empty list
        return []

@router.get("/download/{filename}")
async def get_catalog(filename: str):
    # Instead of downloading directly, we redirect to the Cloudinary URL
    # Or we just return the URL and let the frontend handle it
    from fastapi.responses import RedirectResponse
    
    try:
        # Construct the expected Cloudinary URL for the raw file
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        if not cloud_name:
            raise HTTPException(status_code=500, detail="Cloudinary configuration missing")
            
        url = f"https://res.cloudinary.com/{cloud_name}/raw/upload/v1/aaj_tech/catalogs/{filename}"
        return RedirectResponse(url=url)
    except Exception as e:
        raise HTTPException(status_code=404, detail="File not found")
