"""Patient CRUD + Zoho sync + the patient-triggered agent shortcuts
(onboarding email, contract-signed receipt)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from agents.base import AgentNotConfiguredError, run_agent
from agents.registry import AGENTS
from database import db
from integrations import zoho

router = APIRouter(prefix="/patients", tags=["patients"])


class PatientCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str = ""
    status: str = "new"
    balance_due: float = 0.0
    notes: str = ""


class PatientUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    status: str | None = None
    balance_due: float | None = None
    notes: str | None = None


@router.get("")
def list_patients():
    return list(db.patients.find({}, {"_id": 0}).sort("created_at", -1))


@router.post("")
def create_patient(body: PatientCreate):
    doc = body.model_dump()
    doc["email"] = str(doc["email"])
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    db.patients.insert_one(dict(doc))
    return doc


@router.put("/{patient_id}")
def update_patient(patient_id: str, body: PatientUpdate):
    updates = {k: (str(v) if k == "email" else v)
               for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = db.patients.update_one({"id": patient_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(404, "Patient not found")
    return db.patients.find_one({"id": patient_id}, {"_id": 0})


@router.delete("/{patient_id}")
def delete_patient(patient_id: str):
    result = db.patients.delete_one({"id": patient_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Patient not found")
    return {"deleted": True}


class ZohoSyncRequest(BaseModel):
    worksheet_name: str
    name_column: str = "Name"
    email_column: str = "Email"
    balance_column: str = ""
    phone_column: str = ""


@router.post("/sync-zoho")
def sync_from_zoho(body: ZohoSyncRequest):
    """Import/refresh patients from a worksheet of the assigned Zoho sheet.
    Rows are matched to existing patients by email."""
    try:
        rows = zoho.fetch_records(body.worksheet_name)
    except zoho.ZohoNotConnectedError as exc:
        raise HTTPException(400, str(exc))

    created, updated, skipped = 0, 0, 0
    for row in rows:
        email = str(row.get(body.email_column, "")).strip().lower()
        name = str(row.get(body.name_column, "")).strip()
        if not email or not name:
            skipped += 1
            continue
        fields = {"name": name, "email": email,
                  "updated_at": datetime.now(timezone.utc).isoformat(),
                  "zoho_row": row}
        if body.phone_column and row.get(body.phone_column):
            fields["phone"] = str(row[body.phone_column])
        if body.balance_column and row.get(body.balance_column) not in (None, ""):
            try:
                fields["balance_due"] = float(str(row[body.balance_column]).replace(",", ""))
            except ValueError:
                pass
        existing = db.patients.find_one({"email": email})
        if existing:
            db.patients.update_one({"email": email}, {"$set": fields})
            updated += 1
        else:
            fields.update({"id": str(uuid.uuid4()), "status": "new",
                           "balance_due": fields.get("balance_due", 0.0),
                           "created_at": datetime.now(timezone.utc).isoformat()})
            db.patients.insert_one(fields)
            created += 1
    return {"created": created, "updated": updated, "skipped": skipped}


def _run_onboarding(event: str, patient_id: str, extra: dict):
    patient = db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(404, "Patient not found")
    try:
        return run_agent(
            AGENTS["onboarding"],
            task=f"Handle the '{event}' event for patient {patient['name']} (id {patient_id}).",
            payload={"event": event, "patient_id": patient_id, **extra},
            triggered_by=f"patients_page:{event}",
        )
    except AgentNotConfiguredError as exc:
        raise HTTPException(400, str(exc))


@router.post("/{patient_id}/onboard")
def onboard(patient_id: str):
    return _run_onboarding("onboard", patient_id, {})


class ContractSigned(BaseModel):
    contract_amount: float | None = None
    notes: str = ""


@router.post("/{patient_id}/contract-signed")
def contract_signed(patient_id: str, body: ContractSigned):
    return _run_onboarding("contract_signed", patient_id,
                           {k: v for k, v in body.model_dump().items() if v not in (None, "")})
