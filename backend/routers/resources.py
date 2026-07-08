"""Templates, outbox (emails), generated documents, dashboard stats and
connection settings."""
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

import config
from database import db, mongo_ok
from integrations import mailer, zoho
from services import template_builder

router = APIRouter(tags=["resources"])


# ------------------------------ Templates ---------------------------------

class TemplateUpdate(BaseModel):
    subject: str
    html_body: str


@router.get("/templates")
def list_templates():
    return list(db.templates.find({}, {"_id": 0}))


@router.put("/templates/{key}")
def update_template(key: str, body: TemplateUpdate):
    result = db.templates.update_one({"key": key}, {"$set": {
        "subject": body.subject, "html_body": body.html_body,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }})
    if result.matched_count == 0:
        raise HTTPException(404, "Template not found")
    return db.templates.find_one({"key": key}, {"_id": 0})


@router.post("/templates/{key}/build-from-examples")
def build_template_from_examples(key: str,
                                 files: list[UploadFile] = File(...),
                                 instructions: str = Form("")):
    """Upload example files (HTML / screenshots / PDFs / text) and have the
    Template Builder agent draft this template from them."""
    payload = [(f.filename, f.file.read(), f.content_type or "") for f in files]
    try:
        return template_builder.build_from_examples(key, payload, instructions)
    except template_builder.TemplateBuilderError as exc:
        raise HTTPException(400, str(exc))
    except anthropic.APIError as exc:
        raise HTTPException(502, f"Anthropic API error: {exc}")


# ------------------------------- Outbox -----------------------------------

@router.get("/emails")
def list_emails(limit: int = 100):
    return list(db.emails.find({}, {"_id": 0}).sort("created_at", -1).limit(min(limit, 500)))


# ------------------------------ Documents ---------------------------------

@router.get("/documents")
def list_documents(kind: str | None = None, limit: int = 100):
    query = {"kind": kind} if kind else {}
    return list(db.documents.find(query, {"_id": 0, "path": 0})
                .sort("created_at", -1).limit(min(limit, 500)))


@router.get("/documents/{document_id}/download")
def download_document(document_id: str):
    doc = db.documents.find_one({"id": document_id})
    if not doc or not Path(doc["path"]).exists():
        raise HTTPException(404, "Document not found")
    return FileResponse(doc["path"], media_type="application/pdf",
                        filename=doc["filename"])


# ------------------------------ Dashboard ---------------------------------

@router.get("/dashboard")
def dashboard():
    pending = list(db.patients.aggregate([
        {"$match": {"balance_due": {"$gt": 0}}},
        {"$group": {"_id": None, "total": {"$sum": "$balance_due"},
                    "count": {"$sum": 1}}},
    ]))
    return {
        "patients": db.patients.count_documents({}),
        "agent_runs": db.agent_runs.count_documents({}),
        "emails": db.emails.count_documents({}),
        "documents": db.documents.count_documents({}),
        "pending_dues_total": pending[0]["total"] if pending else 0,
        "pending_dues_count": pending[0]["count"] if pending else 0,
        "recent_runs": list(db.agent_runs.find({}, {"_id": 0, "steps": 0})
                            .sort("started_at", -1).limit(8)),
    }


# ------------------------------ Settings ----------------------------------

@router.get("/settings/connections")
def connections():
    status = config.connection_status()
    ok = mongo_ok()
    status["mongodb"] = {
        "configured": ok,
        "detail": "Connected." if ok
        else f"Cannot reach MongoDB at MONGO_URL ({config.MONGO_URL}). Start it or update backend/.env.",
    }
    return status


@router.post("/settings/test-zoho")
def test_zoho():
    try:
        return {"ok": True, "worksheets": zoho.list_worksheets()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
