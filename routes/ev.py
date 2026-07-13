from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database import get_db
from models import EVProductResponse, EVProductCreate
from bson import ObjectId
from utils.auth import require_admin

router = APIRouter()

def ev_helper(item) -> dict:
    """Convert MongoDB document to a clean dict with string id."""
    return {
        "id": str(item["_id"]),
        "title": item["title"],
        "applications": item.get("applications", ""),
        "details": item.get("details", ""),
        "variants": item.get("variants", []),
        "image": item.get("image", ""),
    }

@router.get("/", response_model=List[EVProductResponse])
def get_ev_products():
    db = get_db()
    items = list(db.ev_products.find())
    return [ev_helper(item) for item in items]

@router.get("/{id}", response_model=EVProductResponse)
def get_ev_product(id: str):
    db = get_db()
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    item = db.ev_products.find_one({"_id": ObjectId(id)})
    if not item:
        raise HTTPException(status_code=404, detail="EV Product not found")
    return ev_helper(item)

@router.post("/", response_model=EVProductResponse)
def create_ev_product(item: EVProductCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    item_dict = item.model_dump()
    result = db.ev_products.insert_one(item_dict)
    item_dict["_id"] = result.inserted_id
    return ev_helper(item_dict)

@router.delete("/{id}")
def delete_ev_product(id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    result = db.ev_products.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="EV Product not found")
    return {"message": "EV Product deleted successfully"}

@router.put("/{id}", response_model=EVProductResponse)
def update_ev_product(id: str, item: EVProductCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    item_dict = item.model_dump()
    result = db.ev_products.update_one(
        {"_id": ObjectId(id)},
        {"$set": item_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="EV Product not found")
        
    updated_item = db.ev_products.find_one({"_id": ObjectId(id)})
    return ev_helper(updated_item)
