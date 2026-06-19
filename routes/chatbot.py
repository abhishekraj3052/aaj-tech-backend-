import os
import shutil
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks, Header, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from database import get_db
from bson import ObjectId
from utils.rag import RagEngine, UPLOAD_DIR
from utils.email import send_enquiry_notification, send_auto_reply

router = APIRouter()
db = get_db()

# Shared secret verification dependency to verify Next.js server is calling
def verify_admin_token(authorization: Optional[str] = Header(None)):
    secret = os.getenv("JWT_SECRET") or "aaj_tech_trading_super_secret_key_2024_premium_industrial"
    expected = f"Bearer {secret}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized admin request")

class ChatRequest(BaseModel):
    message: str
    sessionId: Optional[str] = None

class LeadRequest(BaseModel):
    fullName: str
    email: str
    phone: str
    inquiryType: str
    message: str
    sessionId: Optional[str] = None

@router.post("/chat")
async def chat_query(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    session_id = req.sessionId or str(ObjectId())
    
    # Run the RAG pipeline
    result = RagEngine.answer_query(req.message, db)
    
    # Save conversation log in MongoDB
    user_msg = {
        "sender": "user",
        "text": req.message,
        "timestamp": datetime.now()
    }
    bot_msg = {
        "sender": "bot",
        "text": result["reply"],
        "products": result["products"],
        "categories": result.get("categories", []),
        "timestamp": datetime.now()
    }
    
    db.chatbot_conversations.update_one(
        {"sessionId": session_id},
        {
            "$push": {
                "messages": {
                    "$each": [user_msg, bot_msg]
                }
            },
            "$setOnInsert": {
                "createdAt": datetime.now()
            },
            "$set": {
                "updatedAt": datetime.now()
            }
        },
        upsert=True
    )
    
    return {
        "sessionId": session_id,
        "reply": result["reply"],
        "suggestions": result["suggestions"],
        "products": result["products"],
        "categories": result.get("categories", [])
    }

@router.post("/leads")
async def capture_lead(req: LeadRequest, background_tasks: BackgroundTasks):
    lead_dict = {
        "fullName": req.fullName,
        "email": req.email,
        "phone": req.phone,
        "inquiryType": req.inquiryType,
        "message": req.message,
        "status": "New",
        "createdAt": datetime.now()
    }
    
    # 1. Insert into enquiries collection (main website database)
    res = db.enquiries.insert_one(lead_dict)
    
    # Also save to chatbot_leads for backup
    try:
        db.chatbot_leads.insert_one({**lead_dict, "_id": res.inserted_id})
    except Exception:
        pass
    
    # 2. Update conversation session with lead name
    if req.sessionId:
        db.chatbot_conversations.update_one(
            {"sessionId": req.sessionId},
            {"$set": {"fullName": req.fullName}}
        )
        
    # 3. Reuse existing enquiry notification emails in background
    enquiry_data = {
        "_id": str(res.inserted_id),
        "fullName": req.fullName,
        "email": req.email,
        "phone": req.phone,
        "inquiryType": req.inquiryType,
        "message": req.message
    }
    
    admin_email = os.getenv("EMAIL_USER")
    if admin_email:
        background_tasks.add_task(send_enquiry_notification, admin_email, enquiry_data)
        background_tasks.add_task(send_auto_reply, req.email, enquiry_data)
        
    return {"message": "Inquiry submitted successfully", "id": str(res.inserted_id)}

@router.post("/admin/upload-pdf", dependencies=[Depends(verify_admin_token)])
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
    # Save the file locally to catalogs directory
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Save document metadata to chatbot_documents collection
        doc_record = {
            "filename": file.filename,
            "uploadDate": datetime.now(),
            "size": file_size,
            "chunkCount": 0
        }
        
        db.chatbot_documents.update_one(
            {"filename": file.filename},
            {"$set": doc_record},
            upsert=True
        )
        
        # Optional: Re-index to update vector DB with new PDF immediately
        chunks_indexed = RagEngine.index_data(db)
        
        return {
            "status": "success",
            "filename": file.filename,
            "message": f"PDF catalog indexed successfully into RAG store. Total database chunks: {chunks_indexed}"
        }
    except Exception as e:
        # Cleanup if error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@router.get("/admin/documents", dependencies=[Depends(verify_admin_token)])
async def list_documents():
    try:
        docs = []
        for doc in db.chatbot_documents.find().sort("uploadDate", -1):
            docs.append({
                "id": str(doc["_id"]),
                "filename": doc["filename"],
                "uploadDate": doc["uploadDate"].isoformat() if isinstance(doc["uploadDate"], datetime) else str(doc["uploadDate"]),
                "size": doc.get("size", 0),
                "chunkCount": doc.get("chunkCount", 0)
            })
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents list: {str(e)}")

@router.delete("/admin/documents/{filename}", dependencies=[Depends(verify_admin_token)])
async def delete_document(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            
        db.chatbot_documents.delete_one({"filename": filename})
        
        # Trigger rebuild
        chunks_indexed = RagEngine.index_data(db)
        
        return {
            "status": "success",
            "message": f"Document {filename} deleted and vector DB rebuilt. Total database chunks: {chunks_indexed}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.post("/admin/rebuild-embeddings", dependencies=[Depends(verify_admin_token)])
async def rebuild_embeddings():
    try:
        print("RAG: Rebuilding vector database...")
        chunks_indexed = RagEngine.index_data(db)
        return {
            "status": "success",
            "message": f"Successfully indexed {chunks_indexed} chunks into vector database."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {str(e)}")
