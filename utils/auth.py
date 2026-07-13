import os
import jwt
from fastapi import Request, HTTPException, status, Depends

JWT_SECRET = os.getenv("JWT_SECRET", "aaj_tech_trading_super_secret_key_2024_premium_industrial")

def get_current_user(request: Request) -> dict:
    token = None
    
    # 1. Try to get token from cookies
    if "admin_token" in request.cookies:
        token = request.cookies.get("admin_token")
    
    # 2. Try to get token from Authorization header (fallback/Postman support)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
        
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

def require_admin(payload: dict = Depends(get_current_user)):
    role = payload.get("role")
    # Verify the user has admin or staff permissions
    if role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    return payload
