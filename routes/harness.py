from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database import get_db
from models import HarnessProductResponse, HarnessProductCreate
from bson import ObjectId
from utils.auth import require_admin

router = APIRouter()

def harness_helper(item) -> dict:
    """Convert MongoDB document to a clean dict with string id."""
    return {
        "id": str(item["_id"]),
        "title": item["title"],
        "applications": item.get("applications", ""),
        "details": item.get("details", ""),
        "variants": item.get("variants", []),
        "image": item.get("image", ""),
    }

@router.get("/", response_model=List[HarnessProductResponse])
def get_harness_products():
    db = get_db()
    items = list(db.harness_products.find())
    return [harness_helper(item) for item in items]

@router.get("/{id}", response_model=HarnessProductResponse)
def get_harness_product(id: str):
    db = get_db()
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    item = db.harness_products.find_one({"_id": ObjectId(id)})
    if not item:
        raise HTTPException(status_code=404, detail="Harness Product not found")
    return harness_helper(item)

@router.post("/", response_model=HarnessProductResponse)
def create_harness_product(item: HarnessProductCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    item_dict = item.model_dump()
    result = db.harness_products.insert_one(item_dict)
    item_dict["_id"] = result.inserted_id
    return harness_helper(item_dict)

@router.delete("/{id}")
def delete_harness_product(id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    result = db.harness_products.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Harness Product not found")
    return {"message": "Harness Product deleted successfully"}

@router.put("/{id}", response_model=HarnessProductResponse)
def update_harness_product(id: str, item: HarnessProductCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    item_dict = item.model_dump()
    result = db.harness_products.update_one(
        {"_id": ObjectId(id)},
        {"$set": item_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Harness Product not found")
        
    updated_item = db.harness_products.find_one({"_id": ObjectId(id)})
    return harness_helper(updated_item)
