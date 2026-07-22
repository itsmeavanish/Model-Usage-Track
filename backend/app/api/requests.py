from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.dependencies import get_db
from app.models.enriched_request import EnrichedRequest
from fastapi.responses import StreamingResponse
import csv
import io
import json

router = APIRouter()

@router.get("/")
async def list_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    source: str = None,
    model: str = None,
    application: str = None,
    user_id: str = None,
    provider: str = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(EnrichedRequest).order_by(desc(EnrichedRequest.timestamp))

    if source:
        stmt = stmt.where(EnrichedRequest.source == source)
    if model:
        stmt = stmt.where(EnrichedRequest.model == model)
    if application:
        stmt = stmt.where(EnrichedRequest.application == application)
    if user_id:
        stmt = stmt.where(EnrichedRequest.user_id == user_id)
    if provider:
        stmt = stmt.where(EnrichedRequest.provider == provider)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    requests = result.scalars().all()

    return [
        {
            "id": r.id,
            "request_id": r.request_id,
            "source": r.source,
            "provider": r.provider,
            "timestamp": r.timestamp,
            "model": r.model,
            "total_tokens": r.total_tokens,
            "application": r.application,
            "user_id": r.user_id,
            "is_reconciled": r.is_reconciled
        }
        for r in requests
    ]

@router.get("/export")
async def export_requests(
    format: str = Query("csv", pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(EnrichedRequest).order_by(desc(EnrichedRequest.timestamp)).limit(1000)
    result = await db.execute(stmt)
    requests = result.scalars().all()

    if format == "json":
        data = [
            {
                "request_id": r.request_id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "model": r.model,
                "total_tokens": r.total_tokens,
                "application": r.application
            } for r in requests
        ]
        return StreamingResponse(
            iter([json.dumps(data)]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=usage_export.json"}
        )
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Request ID", "Timestamp", "Model", "Total Tokens", "Application"])
        for r in requests:
            writer.writerow([
                r.request_id,
                r.timestamp.isoformat() if r.timestamp else "",
                r.model,
                r.total_tokens,
                r.application
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=usage_export.csv"}
        )
