"""Patient Portal API — an agentic automation system for patient receipts,
Zoho-sheet-driven emails, dues follow-ups, financial forms and onboarding.

Run:  uvicorn server:app --reload --port 8001
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

import config
from database import mongo_ok
from routers import agents_api, patients, resources
from services.templates import seed_templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("patient-portal")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if mongo_ok():
        seed_templates()
    else:
        logger.warning("MongoDB not reachable at %s — API is up but data "
                       "operations will fail until it is. See /api/settings/connections.",
                       config.MONGO_URL)
    yield


app = FastAPI(title="Patient Portal — Agentic Automation", lifespan=lifespan)

api = APIRouter(prefix="/api")


@api.get("/")
def root():
    return {"service": "patient-portal", "status": "ok"}


api.include_router(patients.router)
api.include_router(agents_api.router)
api.include_router(resources.router)
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
