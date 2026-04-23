from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import AIDecision

router = APIRouter(prefix="/api/decisions", tags=["AI Decisions"])


@router.get("/")
async def list_decisions(
    status: str | None = None,
    product_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(AIDecision).order_by(AIDecision.created_at.desc()).limit(limit)
    if status:
        query = query.where(AIDecision.status == status)
    if product_id:
        query = query.where(AIDecision.product_id == product_id)

    result = await db.execute(query)
    decisions = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "product_id": str(d.product_id),
            "decision_type": d.decision_type,
            "action": d.action,
            "old_value": float(d.old_value) if d.old_value else None,
            "new_value": float(d.new_value) if d.new_value else None,
            "reason": d.reason,
            "confidence": float(d.confidence) if d.confidence else None,
            "status": d.status,
            "urgency": d.context.get("urgency") if d.context else None,
            "created_at": d.created_at.isoformat(),
            "executed_at": d.executed_at.isoformat() if d.executed_at else None,
        }
        for d in decisions
    ]


@router.get("/pending")
async def list_pending_decisions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AIDecision)
        .where(AIDecision.status == "pending")
        .order_by(AIDecision.created_at.desc())
    )
    return [
        {
            "id": str(d.id),
            "product_id": str(d.product_id),
            "action": d.action,
            "old_value": float(d.old_value) if d.old_value else None,
            "new_value": float(d.new_value) if d.new_value else None,
            "reason": d.reason,
            "confidence": float(d.confidence) if d.confidence else None,
            "urgency": d.context.get("urgency") if d.context else None,
            "created_at": d.created_at.isoformat(),
        }
        for d in result.scalars().all()
    ]


@router.post("/{decision_id}/approve")
async def approve_decision(decision_id: UUID, db: AsyncSession = Depends(get_db)):
    decision = await db.get(AIDecision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decisão não encontrada")
    if decision.status != "pending":
        raise HTTPException(status_code=400, detail=f"Decisão já está com status: {decision.status}")

    from datetime import datetime
    decision.status = "approved"
    decision.approved_at = datetime.utcnow()
    await db.flush()

    return {"status": "approved", "decision_id": str(decision_id), "message": "Aprovado. Será executado no próximo ciclo."}


@router.post("/{decision_id}/reject")
async def reject_decision(decision_id: UUID, db: AsyncSession = Depends(get_db)):
    decision = await db.get(AIDecision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decisão não encontrada")
    if decision.status != "pending":
        raise HTTPException(status_code=400, detail=f"Decisão já está com status: {decision.status}")

    decision.status = "rejected"
    await db.flush()

    return {"status": "rejected", "decision_id": str(decision_id)}
