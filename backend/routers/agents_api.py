"""Agent catalog, manual triggering and run history."""
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.base import AgentNotConfiguredError, run_agent
from agents.registry import AGENTS
from database import db

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
def list_agents():
    return [{k: v for k, v in asdict(spec).items() if k not in ("tools", "system_prompt")}
            | {"tools": [t["name"] for t in spec.tools]}
            for spec in AGENTS.values()]


class RunRequest(BaseModel):
    payload: dict = {}
    task: str | None = None


@router.post("/{agent_key}/run")
def trigger_agent(agent_key: str, body: RunRequest):
    spec = AGENTS.get(agent_key)
    if not spec:
        raise HTTPException(404, f"Unknown agent '{agent_key}'")
    task = body.task or f"Run your workflow on the input data below."
    try:
        return run_agent(spec, task=task, payload=body.payload, triggered_by="agents_page")
    except AgentNotConfiguredError as exc:
        raise HTTPException(400, str(exc))


@router.get("/runs")
def list_runs(agent_key: str | None = None, limit: int = 50):
    query = {"agent_key": agent_key} if agent_key else {}
    return list(db.agent_runs.find(query, {"_id": 0})
                .sort("started_at", -1).limit(min(limit, 200)))


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    run = db.agent_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(404, "Run not found")
    return run
