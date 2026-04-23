from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])

USERS_DB: dict[str, str] = {}


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest):
    if data.username in USERS_DB:
        raise HTTPException(status_code=409, detail="Usuário já existe")
    USERS_DB[data.username] = hash_password(data.password)
    token = create_access_token(data.username)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    hashed = USERS_DB.get(data.username)
    if not hashed or not verify_password(data.password, hashed):
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")
    token = create_access_token(data.username)
    return TokenResponse(access_token=token)
