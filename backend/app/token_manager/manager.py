import logging
from datetime import datetime, timedelta

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class TokenManager:
    """Gerencia renovação automática de tokens OAuth para cada plataforma.

    Tokens do Mercado Livre expiram em 6 horas.
    Tokens da Shopee expiram em ~4 horas.
    Tokens da Amazon expiram em 1 hora.
    """

    def __init__(self):
        self._tokens: dict[str, dict] = {}
        self._client = httpx.AsyncClient(timeout=15.0)

    async def get_ml_token(self) -> str:
        cached = self._tokens.get("mercadolivre")
        if cached and cached["expires_at"] > datetime.utcnow():
            return cached["access_token"]

        if not settings.ml_refresh_token:
            return settings.ml_access_token

        try:
            resp = await self._client.post("https://api.mercadolibre.com/oauth/token", json={
                "grant_type": "refresh_token",
                "client_id": settings.ml_client_id,
                "client_secret": settings.ml_client_secret,
                "refresh_token": settings.ml_refresh_token,
            })
            resp.raise_for_status()
            data = resp.json()

            self._tokens["mercadolivre"] = {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", settings.ml_refresh_token),
                "expires_at": datetime.utcnow() + timedelta(seconds=data.get("expires_in", 21600) - 300),
            }
            logger.info("ML token refreshed, expires in %ds", data.get("expires_in", 0))
            return data["access_token"]

        except Exception as e:
            logger.error("ML token refresh failed: %s", e)
            return settings.ml_access_token

    async def get_shopee_token(self) -> str:
        cached = self._tokens.get("shopee")
        if cached and cached["expires_at"] > datetime.utcnow():
            return cached["access_token"]

        if not settings.shopee_partner_key:
            return settings.shopee_access_token

        try:
            import hashlib
            import hmac
            import time

            ts = int(time.time())
            path = "/api/v2/auth/access_token/get"
            base = f"{settings.shopee_partner_id}{path}{ts}"
            sign = hmac.new(settings.shopee_partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()

            resp = await self._client.post(
                f"https://partner.shopeemobile.com{path}",
                params={"partner_id": settings.shopee_partner_id, "timestamp": ts, "sign": sign},
                json={
                    "refresh_token": self._tokens.get("shopee", {}).get("refresh_token", settings.shopee_access_token),
                    "partner_id": settings.shopee_partner_id,
                    "shop_id": settings.shopee_shop_id,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("error"):
                raise Exception(data["message"])

            self._tokens["shopee"] = {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_at": datetime.utcnow() + timedelta(seconds=data.get("expire_in", 14400) - 300),
            }
            logger.info("Shopee token refreshed")
            return data["access_token"]

        except Exception as e:
            logger.error("Shopee token refresh failed: %s", e)
            return settings.shopee_access_token

    async def get_amazon_token(self) -> str:
        cached = self._tokens.get("amazon")
        if cached and cached["expires_at"] > datetime.utcnow():
            return cached["access_token"]

        if not settings.amazon_refresh_token:
            return ""

        try:
            resp = await self._client.post("https://api.amazon.com/auth/o2/token", data={
                "grant_type": "refresh_token",
                "refresh_token": settings.amazon_refresh_token,
                "client_id": settings.amazon_client_id,
                "client_secret": settings.amazon_client_secret,
            })
            resp.raise_for_status()
            data = resp.json()

            self._tokens["amazon"] = {
                "access_token": data["access_token"],
                "expires_at": datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600) - 60),
            }
            logger.info("Amazon token refreshed")
            return data["access_token"]

        except Exception as e:
            logger.error("Amazon token refresh failed: %s", e)
            return ""

    async def close(self):
        await self._client.aclose()


token_manager = TokenManager()
