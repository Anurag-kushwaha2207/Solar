"""Auth router — simple demo auth"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(req: LoginRequest):
    # Demo: accept any credentials
    return {
        "token": "demo-token-urjamind-2026",
        "user": {"name": "Plant Manager", "plant": "Rajkot Foundry", "role": "admin"},
        "message": "Login successful",
    }

@router.get("/me")
async def me():
    return {"name": "Plant Manager", "plant": "Rajkot Precision Foundry", "role": "admin"}
