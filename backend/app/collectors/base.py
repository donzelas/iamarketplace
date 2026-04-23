from abc import ABC, abstractmethod
from datetime import datetime


class BaseCollector(ABC):
    """Classe base para todos os coletores de marketplace."""

    marketplace: str = ""

    @abstractmethod
    async def search_competitors(self, keyword: str, limit: int = 50) -> list[dict]:
        """Busca anúncios concorrentes por palavra-chave."""
        ...

    @abstractmethod
    async def get_product_details(self, product_id: str) -> dict:
        """Retorna detalhes de um anúncio específico."""
        ...

    @abstractmethod
    async def update_price(self, listing_id: str, new_price: float) -> dict:
        """Atualiza preço de um anúncio no marketplace."""
        ...

    async def close(self):
        """Fecha conexões HTTP."""
        if hasattr(self, "client"):
            await self.client.aclose()

    def normalize_result(self, raw: dict) -> dict:
        """Normaliza resultado de qualquer marketplace para formato padrão."""
        return {
            "marketplace": self.marketplace,
            "listing_id": raw.get("listing_id", ""),
            "title": raw.get("title", ""),
            "price": float(raw.get("price", 0)),
            "original_price": raw.get("original_price"),
            "seller": raw.get("seller", ""),
            "free_shipping": raw.get("free_shipping", False),
            "condition": raw.get("condition", "new"),
            "sold_quantity": raw.get("sold_quantity", 0),
            "url": raw.get("url", ""),
            "position": raw.get("position"),
            "collected_at": datetime.utcnow().isoformat(),
        }
