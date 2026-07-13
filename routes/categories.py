from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from database import get_db
from models import CategoryResponse, CategoryCreate
from bson import ObjectId
from utils.auth import require_admin

router = APIRouter()

def category_helper(cat, db=None, counts_map=None) -> dict:
    """Convert MongoDB document to a clean dict with string id."""
    count = cat.get("count", 0)
    cat_id = str(cat["_id"])
    if counts_map is not None:
        count = counts_map.get(cat_id, 0)
    elif db is not None:
        count = db.products.count_documents({"category_id": cat_id})

    return {
        "id": cat_id,
        "name": cat["name"],
        "count": count,
        "description": cat.get("description", None),
        "image": cat.get("image", None),
        "icon": cat.get("icon", None),
        "sequence": cat.get("sequence", 0),
    }

@router.get("/", response_model=List[CategoryResponse])
def get_categories():
    db = get_db()
    categories = list(db.categories.find().sort("sequence", 1))
    
    # Precompute product counts per category in one query
    pipeline = [
        {"$group": {"_id": "$category_id", "count": {"$sum": 1}}}
    ]
    counts = list(db.products.aggregate(pipeline))
    counts_map = {str(item["_id"]): item["count"] for item in counts if item["_id"] is not None}
    
    return [category_helper(cat, db, counts_map) for cat in categories]

@router.post("/", response_model=CategoryResponse)
def create_category(category: CategoryCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    category_dict = category.model_dump()
    result = db.categories.insert_one(category_dict)
    category_dict["_id"] = result.inserted_id
    return category_helper(category_dict, db)

@router.delete("/{category_id}")
def delete_category(category_id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=400, detail="Invalid category ID")
    result = db.categories.delete_one({"_id": ObjectId(category_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted successfully"}

class ReorderRequest(BaseModel):
    category_ids: List[str]

@router.put("/reorder")
def reorder_categories(request: ReorderRequest, admin: dict = Depends(require_admin)):
    db = get_db()
    for index, cat_id in enumerate(request.category_ids):
        if ObjectId.is_valid(cat_id):
            db.categories.update_one(
                {"_id": ObjectId(cat_id)},
                {"$set": {"sequence": index}}
            )
    return {"message": "Categories reordered successfully"}

@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: str, category: CategoryCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=400, detail="Invalid category ID")
    
    category_dict = category.model_dump()
    result = db.categories.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": category_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
        
    updated_cat = db.categories.find_one({"_id": ObjectId(category_id)})
    return category_helper(updated_cat, db)
