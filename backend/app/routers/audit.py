import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog
from app.schemas import AuditLogOut

router = APIRouter(tags=["audit"])


@router.get("/agents/{agent_id}/audit", response_model=list[AuditLogOut])
def get_audit_trail(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(AuditLog)
        .filter(AuditLog.agent_id == agent_id)
        .order_by(AuditLog.created_at.asc())
        .all()
    )
