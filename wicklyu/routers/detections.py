from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from wicklyu.db import get_session
from wicklyu.models import Detection
from wicklyu.schemas import DetectionIn, DetectionOut

router = APIRouter(tags=["detections"])

@router.post("/detections", response_model=DetectionOut, status_code=status.HTTP_201_CREATED)
async def create_detection(payload: DetectionIn, session: AsyncSession = Depends(get_session)):
    det = Detection(symbol=payload.symbol.upper(), timeframe=payload.timeframe or "1D")
    session.add(det)
    await session.commit()
    await session.refresh(det)
    return det

@router.get("/detections/{det_id}", response_model=DetectionOut)
async def read_detection(det_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Detection).where(Detection.id == det_id))
    det = result.scalar_one_or_none()
    if not det:
        raise HTTPException(status_code=404, detail="Detection not found")
    return det

@router.get("/detections", response_model=List[DetectionOut])
async def list_detections(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Detection).order_by(Detection.id.desc()))
    return result.scalars().all()