"""Zoho Sheets integration.

Uses the OAuth2 refresh-token flow (create a "Self Client" at
https://api-console.zoho.com, generate a grant with scope
`ZohoSheet.dataAPI.READ`, exchange it for a refresh token, and put the
credentials in backend/.env). Until connected, agents that need sheet data
receive a clear "not connected" message instead of failing silently.
"""
import time

import requests

import config


class ZohoNotConnectedError(Exception):
    pass


_token_cache = {"access_token": None, "expires_at": 0.0}


def is_configured() -> bool:
    return bool(
        config.ZOHO_CLIENT_ID
        and config.ZOHO_CLIENT_SECRET
        and config.ZOHO_REFRESH_TOKEN
        and config.ZOHO_SHEET_RESOURCE_ID
    )


def _access_token() -> str:
    if not is_configured():
        raise ZohoNotConnectedError(
            "Zoho Sheets is not connected. Set ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, "
            "ZOHO_REFRESH_TOKEN and ZOHO_SHEET_RESOURCE_ID in backend/.env."
        )
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    resp = requests.post(
        f"{config.ZOHO_ACCOUNTS_BASE}/oauth/v2/token",
        params={
            "refresh_token": config.ZOHO_REFRESH_TOKEN,
            "client_id": config.ZOHO_CLIENT_ID,
            "client_secret": config.ZOHO_CLIENT_SECRET,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "access_token" not in data:
        raise ZohoNotConnectedError(f"Zoho token refresh failed: {data}")
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + int(data.get("expires_in", 3600))
    return data["access_token"]


def _sheet_post(payload: dict) -> dict:
    token = _access_token()
    resp = requests.post(
        f"{config.ZOHO_SHEET_API_BASE}/{config.ZOHO_SHEET_RESOURCE_ID}",
        headers={"Authorization": f"Zoho-oauthtoken {token}"},
        data=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def list_worksheets() -> list:
    data = _sheet_post({"method": "worksheet.list"})
    return data.get("worksheet_names") or data.get("worksheets") or []


def fetch_records(worksheet_name: str, count: int = 200) -> list:
    """Return worksheet rows as a list of {header: value} dicts."""
    data = _sheet_post(
        {
            "method": "worksheet.records.fetch",
            "worksheet_name": worksheet_name,
            "count": count,
        }
    )
    return data.get("records", [])
