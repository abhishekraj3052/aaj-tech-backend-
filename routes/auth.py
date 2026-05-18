from fastapi import APIRouter, HTTPException, BackgroundTasks
from database import get_db
from models import SignupRequest, UserResponse
from utils.email import send_welcome_email
import os

from datetime import datetime

router = APIRouter()
db = get_db()

@router.post("/signup", response_model=dict)
async def signup(request: SignupRequest, background_tasks: BackgroundTasks):
    # Check if user already exists
    existing_user = db.users.find_one({"email": request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already registered")
    
    # Create new user in MongoDB
    user_dict = {
        "fullName": request.fullName,
        "email": request.email,
        "role": "user",
        "isActive": False, # User is inactive until password is set
        "createdAt": datetime.now()
    }
    
    # In a real app, you'd generate a secure token for password setting
    # For this demonstration, we'll use a mock reset link
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    reset_link = f"{frontend_url}/set-password?email={request.email}&token=secure-token-123"
    
    result = db.users.insert_one(user_dict)
    
    # Send welcome email in background
    background_tasks.add_task(send_welcome_email, request.email, request.fullName, reset_link)
    
    return {"message": "Signup successful. Please check your email to set your password.", "id": str(result.inserted_id)}
