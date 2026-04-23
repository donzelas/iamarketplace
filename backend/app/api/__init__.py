from .products import router as products_router
from .competitors import router as competitors_router
from .ads import router as ads_router
from .decisions import router as decisions_router
from .dashboard import router as dashboard_router

__all__ = [
    "products_router",
    "competitors_router",
    "ads_router",
    "decisions_router",
    "dashboard_router",
]
