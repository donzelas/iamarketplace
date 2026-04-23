from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Product, ProductListing
from ..schemas import ProductCreate, ProductUpdate, ProductResponse, ListingCreate, ListingResponse

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("/", response_model=list[ProductResponse])
async def list_products(status: str = "active", db: AsyncSession = Depends(get_db)):
    query = select(Product).order_by(Product.name)
    if status != "all":
        query = query.where(Product.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return product


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Product).where(Product.sku == data.sku))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="SKU já existe")

    product = Product(**data.model_dump())
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: UUID, data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.flush()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    product.status = "deleted"
    await db.flush()


# ── Listings ──

@router.get("/{product_id}/listings", response_model=list[ListingResponse])
async def list_product_listings(product_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProductListing).where(ProductListing.product_id == product_id)
    )
    return result.scalars().all()


@router.post("/{product_id}/listings", response_model=ListingResponse, status_code=201)
async def create_listing(product_id: UUID, data: ListingCreate, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    listing = ProductListing(**data.model_dump())
    listing.product_id = product_id
    db.add(listing)
    await db.flush()
    await db.refresh(listing)
    return listing
