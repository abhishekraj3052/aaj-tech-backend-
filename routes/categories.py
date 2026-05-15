from fastapi import APIRouter, HTTPException
from typing import List
from database import get_db
from models import CategoryResponse, CategoryCreate
from bson import ObjectId

router = APIRouter()

def category_helper(cat) -> dict:
    """Convert MongoDB document to a clean dict with string id."""
    return {
        "id": str(cat["_id"]),
        "name": cat["name"],
        "count": cat.get("count", 0),
        "description": cat.get("description", None),
        "image": cat.get("image", None),
        "icon": cat.get("icon", None),
    }

@router.get("/", response_model=List[CategoryResponse])
def get_categories():
    db = get_db()
    categories = list(db.categories.find())
    return [category_helper(cat) for cat in categories]

@router.post("/", response_model=CategoryResponse)
def create_category(category: CategoryCreate):
    db = get_db()
    category_dict = category.model_dump()
    result = db.categories.insert_one(category_dict)
    category_dict["_id"] = result.inserted_id
    return category_helper(category_dict)

@router.delete("/{category_id}")
def delete_category(category_id: str):
    db = get_db()
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=400, detail="Invalid category ID")
    result = db.categories.delete_one({"_id": ObjectId(category_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted successfully"}

@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: str, category: CategoryCreate):
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
    return category_helper(updated_cat)
