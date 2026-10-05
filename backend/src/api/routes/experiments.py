"""Persistent experiment lifecycle API."""

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas import ExperimentCompleteRequest, ExperimentCreateRequest, ExperimentRunResponse
from src.experiment_runs import ExperimentRunStore

router = APIRouter(prefix="/api/experiments", tags=["Experiments"])
experiment_store = ExperimentRunStore()


@router.post("", response_model=ExperimentRunResponse, status_code=201)
def create_experiment(payload: ExperimentCreateRequest):
    return experiment_store.create(payload.name, payload.dataset, payload.configuration)


@router.get("", response_model=list[ExperimentRunResponse])
def list_experiments(limit: int = Query(default=100, ge=1, le=500)):
    return experiment_store.list(limit)


@router.get("/{experiment_id}", response_model=ExperimentRunResponse)
def get_experiment(experiment_id: str):
    result = experiment_store.get(experiment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return result


@router.post("/{experiment_id}/cancel", response_model=ExperimentRunResponse)
def cancel_experiment(experiment_id: str):
    try:
        result = experiment_store.cancel(experiment_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return result


@router.post("/{experiment_id}/complete", response_model=ExperimentRunResponse)
def complete_experiment(experiment_id: str, payload: ExperimentCompleteRequest):
    try:
        result = experiment_store.complete(experiment_id, payload.result, payload.telemetry, payload.environment)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return result
