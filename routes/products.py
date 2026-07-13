from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database import get_db
from models import ProductResponse, ProductCreate
from bson import ObjectId
from utils.auth import require_admin

router = APIRouter()

def product_helper(prod) -> dict:
    """Convert MongoDB document to a clean dict with string id."""
    return {
        "id": str(prod["_id"]),
        "name": prod["name"],
        "sku": prod.get("sku", None),
        "price": prod.get("price", 0.0),
        "stock": prod.get("stock", 0),
        "status": prod.get("status", "active"),
        "category_id": prod.get("category_id", None),
        "description": prod.get("description", None),
        "features": prod.get("features", []),
        "specifications": prod.get("specifications", {}),
        "image": prod.get("image", None),
    }

@router.get("/", response_model=List[ProductResponse])
def get_products():
    db = get_db()
    products = list(db.products.find())
    return [product_helper(prod) for prod in products]

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str):
    db = get_db()
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")
    prod = db.products.find_one({"_id": ObjectId(product_id)})
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_helper(prod)

@router.post("/", response_model=ProductResponse)
def create_product(product: ProductCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    product_dict = product.model_dump()
    result = db.products.insert_one(product_dict)
    product_dict["_id"] = result.inserted_id
    return product_helper(product_dict)

@router.delete("/{product_id}")
def delete_product(product_id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")
    result = db.products.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: str, product: ProductCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    product_dict = product.model_dump()
    result = db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": product_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
        
    updated_prod = db.products.find_one({"_id": ObjectId(product_id)})
    return product_helper(updated_prod)
