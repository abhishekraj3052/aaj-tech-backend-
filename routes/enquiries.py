from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
from datetime import datetime
from database import get_db
from bson import ObjectId
from pydantic import BaseModel, Field
import os
from utils.email import send_enquiry_notification, send_auto_reply
from utils.auth import require_admin

router = APIRouter()
db = get_db()

class EnquiryBase(BaseModel):
    fullName: str
    email: str
    phone: str
    inquiryType: str
    message: str
    productName: Optional[str] = None
    quantity: Optional[int] = None
    totalPrice: Optional[float] = None
    status: str = "New"
    createdAt: datetime = Field(default_factory=datetime.now)

class Enquiry(EnquiryBase):
    id: str

@router.post("/", response_model=dict)
async def create_enquiry(enquiry: EnquiryBase, background_tasks: BackgroundTasks):
    # Basic spam protection: check for empty fields (already handled by Pydantic)
    # and simple validation for corporate email if needed.
    
    enquiry_dict = enquiry.dict()
    result = db.enquiries.insert_one(enquiry_dict)
    
    # Send emails in background to not block the response
    admin_email = os.getenv("EMAIL_USER")
    background_tasks.add_task(send_enquiry_notification, admin_email, enquiry_dict)
    background_tasks.add_task(send_auto_reply, enquiry.email, enquiry_dict)
    
    return {"id": str(result.inserted_id), "message": "Enquiry submitted successfully"}

@router.get("/", response_model=List[dict])
def get_enquiries():
    enquiries = []
    for enq in db.enquiries.find().sort("createdAt", -1):
        enq["id"] = str(enq["_id"])
        del enq["_id"]
        enquiries.append(enq)
    return enquiries

@router.put("/{enquiry_id}/status", response_model=dict)
def update_enquiry_status(enquiry_id: str, status: str, admin: dict = Depends(require_admin)):
    result = db.enquiries.update_one(
        {"_id": ObjectId(enquiry_id)},
        {"$set": {"status": status}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return {"message": "Status updated successfully"}

@router.delete("/{enquiry_id}", response_model=dict)
def delete_enquiry(enquiry_id: str, admin: dict = Depends(require_admin)):
    result = db.enquiries.delete_one({"_id": ObjectId(enquiry_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return {"message": "Enquiry deleted successfully"}
