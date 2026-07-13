from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import cloudinary.uploader
import cloudinary.api
import os
from utils.auth import require_admin

router = APIRouter()

@router.post("/upload")
async def upload_ev_catalog(file: UploadFile = File(...), admin: dict = Depends(require_admin)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Upload the PDF directly to Cloudinary as a raw file in chunked mode in the ev_catalogs folder
        result = cloudinary.uploader.upload_large(
            file.file,
            folder="aaj_tech/ev_catalogs",
            resource_type="raw",
            public_id=file.filename,
            chunk_size=6000000
        )
        return {"filename": file.filename, "status": "success", "url": result.get("secure_url")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save EV catalog to Cloudinary: {str(e)}")

@router.get("/")
async def list_ev_catalogs():
    try:
        # Query Cloudinary for files in the aaj_tech/ev_catalogs folder
        resources = cloudinary.api.resources(
            type="upload", 
            prefix="aaj_tech/ev_catalogs/", 
            resource_type="raw"
        )
        
        catalogs = []
        for res in resources.get('resources', []):
            # Extract filename from public_id
            filename = res['public_id'].split('/')[-1]
            if filename.endswith('.pdf'):
                catalogs.append({
                    "name": filename,
                    "url": f"/api/ev-catalog/download/{filename}"
                })
        return catalogs
    except Exception as e:
        # If folder doesn't exist yet or other error, return empty list
        return []

@router.get("/download/{filename}")
async def get_ev_catalog(filename: str):
    import cloudinary.utils
    from fastapi.responses import StreamingResponse
    import os
    
    try:
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        if not cloud_name:
            raise HTTPException(status_code=500, detail="Cloudinary configuration missing")
            
        public_id = f"aaj_tech/ev_catalogs/{filename}"
        url, _ = cloudinary.utils.cloudinary_url(
            public_id,
            resource_type="raw",
            type="upload",
            secure=True,
            sign_url=True
        )
        
        try:
            import requests
            def stream_content():
                r = requests.get(url, stream=True)
                if r.status_code != 200:
                    cld_error = r.headers.get("x-cld-error", "Unauthorized")
                    print(f"CLOUDINARY DOWNLOAD ERROR: {cld_error}")
                    raise Exception(f"Cloudinary error: {cld_error}")
                for chunk in r.iter_content(chunk_size=8192):
                    yield chunk
            return StreamingResponse(
                stream_content(),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename={filename}",
                    "Access-Control-Allow-Origin": "*"
                }
            )
        except Exception as ex:
            import urllib.request
            from urllib.error import HTTPError
            def stream_content_urllib():
                try:
                    req = urllib.request.Request(url)
                    response = urllib.request.urlopen(req)
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        yield chunk
                except HTTPError as he:
                    cld_error = he.headers.get("x-cld-error", "Unauthorized (Please check if PDF delivery is restricted in Cloudinary Settings > Security)")
                    print(f"CLOUDINARY DOWNLOAD ERROR: {cld_error}")
                    raise Exception(f"Cloudinary error: {cld_error}")
            return StreamingResponse(
                stream_content_urllib(),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename={filename}",
                    "Access-Control-Allow-Origin": "*"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF Error: {str(e)}")
