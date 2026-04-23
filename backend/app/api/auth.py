import logging

import httpx
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import create_access_token, hash_password, verify_password
from ..config import settings
from ..database import get_db
from ..models import SystemConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

USERS_DB: dict[str, str] = {}

ML_AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
ML_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
ML_REDIRECT_URI = "https://www.google.com/"


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MLCodeRequest(BaseModel):
    code: str


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


# ── Mercado Livre OAuth ──

@router.get("/mercadolivre/authorize")
async def ml_authorize():
    """Redireciona para a página de autorização do Mercado Livre."""
    if not settings.ml_client_id:
        raise HTTPException(status_code=400, detail="ML_CLIENT_ID não configurado no .env")

    url = (
        f"{ML_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={settings.ml_client_id}"
        f"&redirect_uri={ML_REDIRECT_URI}"
    )
    return RedirectResponse(url)


@router.get("/mercadolivre/callback")
async def ml_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Recebe o code do ML e troca por access_token + refresh_token."""

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(ML_TOKEN_URL, json={
            "grant_type": "authorization_code",
            "client_id": settings.ml_client_id,
            "client_secret": settings.ml_client_secret,
            "code": code,
            "redirect_uri": ML_REDIRECT_URI,
        })

    if resp.status_code != 200:
        logger.error("ML token exchange failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=400, detail=f"Erro ao trocar code: {resp.text}")

    data = resp.json()
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    user_id = data.get("user_id", "")
    expires_in = data.get("expires_in", 21600)

    await _save_ml_tokens(db, access_token, refresh_token, user_id, expires_in)

    logger.info("ML OAuth success: user_id=%s, expires_in=%ds", user_id, expires_in)

    return {
        "status": "success",
        "message": "Mercado Livre conectado com sucesso!",
        "user_id": user_id,
        "expires_in": expires_in,
    }


@router.post("/mercadolivre/code")
async def ml_exchange_code(data: MLCodeRequest, db: AsyncSession = Depends(get_db)):
    """Troca um code manualmente (alternativa ao callback automático)."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(ML_TOKEN_URL, json={
            "grant_type": "authorization_code",
            "client_id": settings.ml_client_id,
            "client_secret": settings.ml_client_secret,
            "code": data.code,
            "redirect_uri": ML_REDIRECT_URI,
        })

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Erro: {resp.text}")

    token_data = resp.json()
    await _save_ml_tokens(
        db,
        token_data["access_token"],
        token_data["refresh_token"],
        token_data.get("user_id", ""),
        token_data.get("expires_in", 21600),
    )

    return {"status": "success", "message": "Tokens salvos!", "user_id": token_data.get("user_id")}


@router.post("/mercadolivre/refresh")
async def ml_refresh_tokens(db: AsyncSession = Depends(get_db)):
    """Renova os tokens do ML usando o refresh_token salvo."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == "ml_refresh_token"))
    config = result.scalar_one_or_none()
    refresh_token = config.value.get("token") if config else settings.ml_refresh_token

    if not refresh_token:
        raise HTTPException(status_code=400, detail="Nenhum refresh_token disponível")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(ML_TOKEN_URL, json={
            "grant_type": "refresh_token",
            "client_id": settings.ml_client_id,
            "client_secret": settings.ml_client_secret,
            "refresh_token": refresh_token,
        })

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Erro ao renovar: {resp.text}")

    data = resp.json()
    await _save_ml_tokens(db, data["access_token"], data["refresh_token"], data.get("user_id", ""), data.get("expires_in", 21600))

    logger.info("ML tokens refreshed successfully")
    return {"status": "success", "message": "Tokens renovados!"}


@router.get("/mercadolivre/status")
async def ml_status(db: AsyncSession = Depends(get_db)):
    """Verifica se o ML está conectado e testa o token."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == "ml_access_token"))
    config = result.scalar_one_or_none()
    token = config.value.get("token") if config else settings.ml_access_token

    if not token:
        return {"connected": False, "message": "Nenhum token configurado"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.mercadolibre.com/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    if resp.status_code == 200:
        user = resp.json()
        return {
            "connected": True,
            "user_id": user.get("id"),
            "nickname": user.get("nickname"),
            "site_id": user.get("site_id"),
        }

    return {"connected": False, "message": f"Token inválido ou expirado (status {resp.status_code})"}


async def _save_ml_tokens(db: AsyncSession, access_token: str, refresh_token: str, user_id: str, expires_in: int):
    for key, value in [
        ("ml_access_token", {"token": access_token, "user_id": user_id, "expires_in": expires_in}),
        ("ml_refresh_token", {"token": refresh_token}),
    ]:
        result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            db.add(SystemConfig(key=key, value=value, description=f"Mercado Livre {key}"))
    await db.flush()
