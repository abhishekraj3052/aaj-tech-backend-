from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database import get_db
from models import BlogResponse, BlogCreate
from bson import ObjectId
from utils.auth import require_admin

router = APIRouter()

def blog_helper(blog) -> dict:
    """Convert MongoDB document to a clean dict with string id."""
    return {
        "id": str(blog["_id"]),
        "title": blog["title"],
        "excerpt": blog.get("excerpt", ""),
        "content": blog.get("content", ""),
        "category": blog.get("category", ""),
        "date": blog.get("date", ""),
        "image": blog.get("image", ""),
        "author": blog.get("author", ""),
        "read_time": blog.get("read_time", ""),
    }

@router.get("/", response_model=List[BlogResponse])
def get_blogs():
    db = get_db()
    blogs = list(db.blogs.find().sort("_id", -1))
    return [blog_helper(blog) for blog in blogs]

@router.get("/{blog_id}", response_model=BlogResponse)
def get_blog(blog_id: str):
    db = get_db()
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=400, detail="Invalid blog ID")
    blog = db.blogs.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    return blog_helper(blog)

@router.post("/", response_model=BlogResponse)
def create_blog(blog: BlogCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    blog_dict = blog.model_dump()
    result = db.blogs.insert_one(blog_dict)
    blog_dict["_id"] = result.inserted_id
    return blog_helper(blog_dict)

@router.put("/{blog_id}", response_model=BlogResponse)
def update_blog(blog_id: str, blog: BlogCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=400, detail="Invalid blog ID")
    
    blog_dict = blog.model_dump()
    result = db.blogs.update_one(
        {"_id": ObjectId(blog_id)},
        {"$set": blog_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    blog_dict["_id"] = ObjectId(blog_id)
    return blog_helper(blog_dict)

@router.delete("/{blog_id}")
def delete_blog(blog_id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=400, detail="Invalid blog ID")
    result = db.blogs.delete_one({"_id": ObjectId(blog_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Blog not found")
    return {"message": "Blog deleted successfully"}
