import base64
import logging
import os
import threading
import time

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

API_BASE = "https://api.tme.eu"

TME_APP_TOKEN = os.getenv("TME_APP_TOKEN", "")
TME_APP_SECRET = os.getenv("TME_APP_SECRET", "")
TME_COUNTRY = os.getenv("TME_COUNTRY", "PL")
TME_LANGUAGE = os.getenv("TME_LANGUAGE", "EN").lower()
TME_CURRENCY = os.getenv("TME_CURRENCY", "PLN")

_session = requests.Session()
_access_token = ""
_token_expires_at = 0.0
_token_lock = threading.Lock()


def _fetch_token() -> None:
    """Obtain an OAuth 2.0 access token with the client-credentials grant."""
    global _access_token, _token_expires_at
    if not TME_APP_TOKEN or not TME_APP_SECRET:
        raise ValueError("TME_APP_TOKEN and TME_APP_SECRET must be set")

    basic = base64.b64encode(f"{TME_APP_TOKEN}:{TME_APP_SECRET}".encode()).decode()
    resp = _session.post(
        f"{API_BASE}/auth/token",
        headers={"Authorization": f"Basic {basic}"},
        data={"grant_type": "client_credentials"},
        timeout=30,
    )
    data = _json(resp)
    if resp.status_code != 200 or "access_token" not in data:
        raise RuntimeError(f"TME auth error ({resp.status_code}): {data.get('message', data)}")

    _access_token = data["access_token"]
    # Refresh a little early so an in-flight request never hits an expired token.
    _token_expires_at = time.time() + max(int(data.get("expires_in", 300)) - 30, 0)
    logger.info("Obtained TME access token")


def _get_token() -> str:
    with _token_lock:
        if not _access_token or time.time() >= _token_expires_at:
            _fetch_token()
        return _access_token


def _json(resp: requests.Response) -> dict:
    try:
        data = resp.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _make_request(endpoint: str, params: dict | None = None) -> dict:
    """Make an authenticated GET request to the TME API v2.

    Args:
        endpoint: API path (e.g. "products/search")
        params: Query parameters. List values are sent as `key[]=v1&key[]=v2`.

    Returns:
        The `data` object of the JSON response.
    """
    query = {"country": TME_COUNTRY}
    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, list):
            query[f"{key}[]"] = value
        elif isinstance(value, bool):
            query[key] = "true" if value else "false"
        else:
            query[key] = value

    url = f"{API_BASE}/{endpoint}"
    headers = {"Accept-Language": TME_LANGUAGE}

    for attempt in range(2):
        headers["Authorization"] = f"Bearer {_get_token()}"
        logger.info(f"GET {url}")
        resp = _session.get(url, params=query, headers=headers, timeout=30)
        if resp.status_code == 401 and attempt == 0:
            with _token_lock:
                _fetch_token()
            continue
        break

    data = _json(resp)
    if resp.status_code != 200:
        details = data.get("error_data") or ""
        raise RuntimeError(f"TME API error ({resp.status_code}): {data.get('message', '')} {details}".strip())

    if data.get("status") != "OK":
        raise RuntimeError(f"TME API error: {data.get('message', data)}")

    return data.get("data", data)
