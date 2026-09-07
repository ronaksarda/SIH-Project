from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.supabase import supabase
from pydantic import BaseModel

router = APIRouter()
security = HTTPBearer()

class User(BaseModel):
    id: str
    email: str
    role: str

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials
    try:
        user_response = supabase.auth.get_user(token)
        user_data = user_response.user
        
        # Now fetch the profile to get the role
        profile_response = supabase.table("profiles").select("*").eq("id", user_data.id).execute()
        
        if not profile_response.data:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Profile not found for user",
            )
            
        profile = profile_response.data[0]
        
        return User(
            id=user_data.id,
            email=user_data.email,
            role=profile.get("role", "inspector")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
