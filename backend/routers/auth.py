"""Auth router — Firebase token-authenticated user profile"""
from fastapi import APIRouter, Depends
from auth_middleware import get_current_user

router = APIRouter()


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {
        "uid": user.get("uid"),
        "name": user.get("name", "Plant Manager"),
        "email": user.get("email"),
        "plant": f"Plant-{user.get('uid', 'demo')[:8]}",
        "role": "admin",
        "auth_source": user.get("source"),
    }
