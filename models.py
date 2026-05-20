from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class CategoryBase(BaseModel):
    name: str
    count: Optional[int] = 0
    description: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    sequence: Optional[int] = 0

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(BaseModel):
    id: str
    name: str
    count: int = 0
    description: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    sequence: int = 0

    model_config = {"from_attributes": True}

class ProductBase(BaseModel):
    name: str
    sku: Optional[str] = None
    price: Optional[float] = 0.0
    stock: Optional[int] = 0
    status: Optional[str] = "active"
    category_id: Optional[str] = None
    description: Optional[str] = None
    features: Optional[List[str]] = []
    image: Optional[str] = None
    
    # Technical Specifications (stored in a dictionary for flexibility)
    specifications: Optional[Dict[str, Any]] = {}

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: str

    model_config = {"from_attributes": True}

class BlogBase(BaseModel):
    title: str
    excerpt: str
    content: str
    category: str
    date: str
    image: str
    author: str
    read_time: str

class BlogCreate(BlogBase):
    pass

class BlogResponse(BlogBase):
    id: str
    model_config = {"from_attributes": True}

class ClientBase(BaseModel):
    name: str
    type: str = "Client"
    location: Optional[str] = None
    totalOrders: Optional[int] = 0
    image: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id: str
    model_config = {"from_attributes": True}

class UserBase(BaseModel):
    fullName: str
    email: str
    role: str = "user"
    isActive: bool = True

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: str
    model_config = {"from_attributes": True}

class SignupRequest(BaseModel):
    fullName: str
    email: str

class HarnessProductBase(BaseModel):
    title: str
    applications: Optional[str] = None
    details: Optional[str] = None
    variants: Optional[List[str]] = []
    image: Optional[str] = None

class HarnessProductCreate(HarnessProductBase):
    pass

class HarnessProductResponse(HarnessProductBase):
    id: str
    model_config = {"from_attributes": True}
