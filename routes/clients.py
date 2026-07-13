from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database import get_db
from models import ClientResponse, ClientCreate
from bson import ObjectId
from utils.auth import require_admin

router = APIRouter()

def client_helper(client) -> dict:
    """Convert MongoDB document to a clean dict with string id."""
    return {
        "id": str(client["_id"]),
        "name": client.get("name", ""),
        "type": client.get("type", "Client"),
        "location": client.get("location", None),
        "totalOrders": client.get("totalOrders", 0),
        "image": client.get("image", None),
        "website": client.get("website", None),
        "description": client.get("description", None),
    }

@router.get("/", response_model=List[ClientResponse])
def get_clients():
    db = get_db()
    clients = list(db.clients.find())
    return [client_helper(client) for client in clients]

@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: str):
    db = get_db()
    if not ObjectId.is_valid(client_id):
        raise HTTPException(status_code=400, detail="Invalid client ID")
    client = db.clients.find_one({"_id": ObjectId(client_id)})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client_helper(client)

@router.post("/", response_model=ClientResponse)
def create_client(client: ClientCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    client_dict = client.model_dump()
    result = db.clients.insert_one(client_dict)
    client_dict["_id"] = result.inserted_id
    return client_helper(client_dict)

@router.put("/{client_id}", response_model=ClientResponse)
def update_client(client_id: str, client: ClientCreate, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(client_id):
        raise HTTPException(status_code=400, detail="Invalid client ID")
    
    client_dict = client.model_dump()
    result = db.clients.update_one(
        {"_id": ObjectId(client_id)},
        {"$set": client_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    updated_client = db.clients.find_one({"_id": ObjectId(client_id)})
    return client_helper(updated_client)

@router.delete("/{client_id}")
def delete_client(client_id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    if not ObjectId.is_valid(client_id):
        raise HTTPException(status_code=400, detail="Invalid client ID")
    result = db.clients.delete_one({"_id": ObjectId(client_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}
