"""API surface for the EcoRAG provenance and audit layer."""

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import (
    AuditAnchorRequest,
    AuditAnchorResponse,
    AuditBatchAnchorRequest,
    AuditProofResponse,
    AuditVerificationResponse,
    AuditVerifyRequest,
)
from src.audit import AuditService

router = APIRouter(prefix="/api/audit", tags=["Audit & Provenance"])
audit_service = AuditService()


@router.post("/anchor", response_model=AuditAnchorResponse, status_code=201)
def anchor_record(payload: AuditAnchorRequest):
    """Create a tamper-evident local anchor for one off-chain audit record."""
    try:
        return audit_service.anchor(
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            payload=payload.payload,
            schema_version=payload.schema_version,
        )
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/batch/anchor", response_model=list[AuditAnchorResponse], status_code=201)
def anchor_batch(payload: AuditBatchAnchorRequest):
    """Anchor up to 500 records using one Merkle root and one local ledger block."""
    try:
        records = [
            (record.entity_type, record.entity_id, record.payload, record.schema_version)
            for record in payload.records
        ]
        return audit_service.anchor_batch(records)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/experiments", response_model=list[AuditAnchorResponse])
def list_experiment_anchors(limit: int = Query(default=100, ge=1, le=500)):
    """List recently anchored experiment records for a client-side audit dashboard."""
    records = audit_service.list_records(entity_type="experiment", limit=limit)
    return [
        {
            **record,
            "transaction_hash": None,
            "status": "anchored_local",
            "anchored_at": record.pop("created_at"),
        }
        for record in records
    ]


@router.get("/{entity_id}/proof", response_model=AuditProofResponse)
def get_experiment_proof(entity_id: str):
    """Return a portable Merkle proof for independently verifying an experiment."""
    result = audit_service.proof(entity_id, entity_type="experiment")
    if result is None:
        raise HTTPException(status_code=404, detail="No audit anchor found for this experiment.")
    return result


@router.get("/{entity_id}", response_model=AuditAnchorResponse)
def get_experiment_anchor(entity_id: str):
    """Return the latest local audit anchor for an experiment."""
    record = audit_service.latest_for_entity(entity_id, entity_type="experiment")
    if record is None:
        raise HTTPException(status_code=404, detail="No audit anchor found for this experiment.")
    return {
        "audit_record_id": record["id"],
        "entity_type": record["entity_type"],
        "entity_id": record["entity_id"],
        "payload_hash": record["payload_hash"],
        "merkle_root": record["merkle_root"],
        "anchor_type": record["anchor_type"],
        "block_number": record["block_number"],
        "block_hash": record["block_hash"],
        "transaction_hash": None,
        "status": "anchored_local",
        "anchored_at": record["created_at"],
    }


@router.post("/{entity_id}/verify", response_model=AuditVerificationResponse)
def verify_experiment_anchor(entity_id: str, payload: AuditVerifyRequest):
    """Rehash a record and compare it with its anchored Merkle block."""
    try:
        result = audit_service.verify(
            entity_id=entity_id,
            entity_type=payload.entity_type,
            payload=payload.payload,
        )
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="No audit anchor found for this entity.")
    return result
